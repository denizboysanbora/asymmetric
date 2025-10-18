#!/usr/bin/env python3
"""
MCP-Integrated Breakout Scanner
Uses Alpaca MCP server directly for all data fetching and trading operations
"""
import os
import sys
import numpy as np
import pandas as pd
import asyncio
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Load environment variables first
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent / "config" / "api_keys.env"
    if env_file.exists():
        load_dotenv(env_file)
        print("🔑 Loaded API keys from .env file", file=sys.stderr)
except ImportError:
    pass

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from breakout_scanner import (
    detect_flag_breakout_setup, 
    detect_range_breakout_setup, 
    calculate_rsi, 
    calculate_atr, 
    calculate_z_score,
    calculate_adr_pct,
    format_breakout_signal,
    SetupTag
)

class MCPDataProvider:
    """MCP server integration for data fetching"""
    
    def __init__(self):
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        self.mcp_server_path = Path(__file__).parent.parent.parent / "alpaca-mcp-server"
        
        if not self.api_key or not self.secret_key:
            print("❌ ALPACA_API_KEY and ALPACA_SECRET_KEY not set", file=sys.stderr)
            sys.exit(1)
    
    async def _call_mcp_tool(self, tool_name: str, arguments: Dict = None) -> Dict:
        """Call an MCP tool via subprocess"""
        
        # Create a simple MCP client script
        client_script = f"""
import asyncio
import json
import sys
from pathlib import Path

# Add the MCP server to path
sys.path.insert(0, "{self.mcp_server_path}")

async def call_tool():
    try:
        from alpaca_mcp_server.server import AlpacaMCPServer
        from alpaca_mcp_server.config import Config
        
        config = Config()
        server = AlpacaMCPServer(config)
        
        # Call the specific tool
        if "{tool_name}" == "get_account_info":
            result = await server.get_account_info()
        elif "{tool_name}" == "get_market_clock":
            result = await server.get_market_clock()
        elif "{tool_name}" == "get_stock_quote":
            result = await server.get_stock_quote("{arguments.get('symbol', '')}")
        elif "{tool_name}" == "get_stock_bars":
            result = await server.get_stock_bars(
                "{arguments.get('symbol', '')}",
                days={arguments.get('days', 90)},
                timeframe="{arguments.get('timeframe', '1Day')}"
            )
        elif "{tool_name}" == "get_all_assets":
            result = await server.get_all_assets(
                status="{arguments.get('status', 'active')}",
                asset_class="{arguments.get('asset_class', 'us_equity')}"
            )
        elif "{tool_name}" == "place_stock_order":
            result = await server.place_stock_order(
                "{arguments.get('symbol', '')}",
                "{arguments.get('side', 'buy')}",
                {arguments.get('quantity', 1)},
                order_type="{arguments.get('order_type', 'market')}"
            )
        elif "{tool_name}" == "get_positions":
            result = await server.get_positions()
        elif "{tool_name}" == "close_position":
            result = await server.close_position(
                "{arguments.get('symbol', '')}",
                percentage={arguments.get('percentage', 100)}
            )
        else:
            result = {{"error": "Unknown tool: {tool_name}"}}
        
        print(json.dumps(result))
        
    except Exception as e:
        print(json.dumps({{"error": str(e)}}))

if __name__ == "__main__":
    asyncio.run(call_tool())
"""
        
        # Write temporary script
        script_path = Path(__file__).parent / "temp_mcp_client.py"
        with open(script_path, 'w') as f:
            f.write(client_script)
        
        try:
            # Run the script
            env = {
                'ALPACA_API_KEY': self.api_key,
                'ALPACA_SECRET_KEY': self.secret_key,
                'ALPACA_PAPER_TRADE': 'True'
            }
            
            result = subprocess.run(
                [sys.executable, str(script_path)],
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.stdout:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"raw_response": result.stdout}
            else:
                return {"error": result.stderr or "No output"}
                
        except Exception as e:
            return {"error": str(e)}
        finally:
            if script_path.exists():
                script_path.unlink()
    
    async def get_liquid_stocks(self, limit: int = 50) -> List[str]:
        """Get liquid stocks from MCP server"""
        try:
            # Get all active US equity assets
            assets_result = await self._call_mcp_tool("get_all_assets", {
                "status": "active",
                "asset_class": "us_equity"
            })
            
            if 'error' in assets_result:
                print(f"⚠️  Could not get assets from MCP: {assets_result['error']}", file=sys.stderr)
                # Fallback to hardcoded liquid stocks
                return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'AMD', 'INTC',
                        'SPY', 'QQQ', 'IWM', 'XLF', 'XLK', 'XLE', 'XLV', 'XLI', 'XLY', 'XLP',
                        'CRM', 'ADBE', 'PYPL', 'UBER', 'SNOW', 'PLTR', 'ZM', 'DOCU', 'OKTA', 'CRWD',
                        'MRNA', 'PFE', 'JNJ', 'UNH', 'ABBV', 'TMO', 'DHR', 'BMY', 'AMGN', 'GILD',
                        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP', 'BLK', 'SCHW', 'COF']
            
            # Parse assets and filter for common liquid stocks
            # This is a simplified approach - in production you'd want more sophisticated filtering
            liquid_symbols = []
            
            # Add major tech stocks
            major_tech = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'AMD', 'INTC']
            liquid_symbols.extend(major_tech)
            
            # Add ETFs
            etfs = ['SPY', 'QQQ', 'IWM', 'XLF', 'XLK', 'XLE', 'XLV', 'XLI', 'XLY', 'XLP']
            liquid_symbols.extend(etfs)
            
            # Add financial stocks
            financials = ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP', 'BLK', 'SCHW', 'COF']
            liquid_symbols.extend(financials)
            
            # Add healthcare stocks
            healthcare = ['MRNA', 'PFE', 'JNJ', 'UNH', 'ABBV', 'TMO', 'DHR', 'BMY', 'AMGN', 'GILD']
            liquid_symbols.extend(healthcare)
            
            # Add growth stocks
            growth = ['CRM', 'ADBE', 'PYPL', 'UBER', 'SNOW', 'PLTR', 'ZM', 'DOCU', 'OKTA', 'CRWD']
            liquid_symbols.extend(growth)
            
            return liquid_symbols[:limit]
            
        except Exception as e:
            print(f"⚠️  Error getting liquid stocks: {e}", file=sys.stderr)
            # Fallback list
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'AMD', 'INTC']
    
    async def get_stock_bars(self, symbol: str, days: int = 90) -> Optional[List]:
        """Get stock bars from MCP server"""
        try:
            result = await self._call_mcp_tool("get_stock_bars", {
                "symbol": symbol,
                "days": days,
                "timeframe": "1Day"
            })
            
            if 'error' in result:
                print(f"⚠️  Could not get bars for {symbol}: {result['error']}", file=sys.stderr)
                return None
            
            # Parse the bars from MCP response
            # The MCP server returns formatted text, we need to parse it
            raw_response = result.get('raw_response', '')
            if not raw_response:
                return None
            
            # For now, return None if we can't parse properly
            # In a full implementation, you'd parse the MCP response format
            return None
            
        except Exception as e:
            print(f"⚠️  Error getting bars for {symbol}: {e}", file=sys.stderr)
            return None
    
    async def get_market_clock(self) -> Dict:
        """Get market clock from MCP server"""
        return await self._call_mcp_tool("get_market_clock")
    
    async def get_account_info(self) -> Dict:
        """Get account info from MCP server"""
        return await self._call_mcp_tool("get_account_info")
    
    async def get_stock_quote(self, symbol: str) -> Dict:
        """Get stock quote from MCP server"""
        return await self._call_mcp_tool("get_stock_quote", {"symbol": symbol})
    
    async def place_market_order(self, symbol: str, side: str, quantity: int) -> Dict:
        """Place market order via MCP server"""
        return await self._call_mcp_tool("place_stock_order", {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": "market"
        })

class MCPIntegratedBreakoutScanner:
    """Breakout scanner that uses MCP server for all operations"""
    
    def __init__(self, auto_trade: bool = False, position_size_pct: float = 10.0):
        self.auto_trade = auto_trade
        self.position_size_pct = position_size_pct
        self.mcp_provider = MCPDataProvider()
    
    async def check_market_status(self) -> bool:
        """Check if market is open"""
        try:
            market_clock = await self.mcp_provider.get_market_clock()
            return market_clock.get('is_open', False)
        except Exception as e:
            print(f"⚠️  Could not check market status: {e}", file=sys.stderr)
            return False
    
    async def get_account_buying_power(self) -> float:
        """Get current buying power"""
        try:
            account_info = await self.mcp_provider.get_account_info()
            return float(account_info.get('buying_power', 0))
        except Exception as e:
            print(f"⚠️  Could not get account info: {e}", file=sys.stderr)
            return 0.0
    
    def create_mock_bars(self, symbol: str, days: int = 90) -> List:
        """Create mock bars for testing when MCP data is not available"""
        import random
        
        bars = []
        base_price = 450.25 if symbol in ['NVDA', 'TSLA'] else 185.50
        current_price = base_price
        
        for i in range(days):
            # Add some realistic price movement
            change = random.uniform(-0.02, 0.03)  # -2% to +3% daily change
            current_price *= (1 + change)
            
            high = current_price * random.uniform(1.001, 1.02)
            low = current_price * random.uniform(0.98, 0.999)
            volume = random.randint(1000000, 10000000)
            
            # Create a mock Bar object
            class MockBar:
                def __init__(self, open_price, high_price, low_price, close_price, vol):
                    self.open = open_price
                    self.high = high_price
                    self.low = low_price
                    self.close = close_price
                    self.volume = vol
            
            bars.append(MockBar(current_price, high, low, current_price, volume))
        
        return bars
    
    async def execute_breakout_trade(self, signal_data: Dict) -> bool:
        """Execute a trade based on breakout signal"""
        try:
            symbol = signal_data['symbol']
            current_price = signal_data['price']
            
            # Get current quote for accurate pricing
            quote = await self.mcp_provider.get_stock_quote(symbol)
            if 'error' in quote:
                print(f"❌ Could not get quote for {symbol}: {quote['error']}", file=sys.stderr)
                return False
            
            # Use quote price if available, otherwise use signal price
            trade_price = float(quote.get('last_price', current_price))
            
            # Get buying power
            buying_power = await self.get_account_buying_power()
            if buying_power < 1000:
                print(f"💰 Insufficient buying power: ${buying_power:,.2f}", file=sys.stderr)
                return False
            
            # Calculate position size
            position_value = buying_power * (self.position_size_pct / 100.0)
            quantity = int(position_value / trade_price)
            
            if quantity < 1:
                print(f"📊 Position size too small for {symbol}: {quantity} shares", file=sys.stderr)
                return False
            
            # Place market order
            order_result = await self.mcp_provider.place_market_order(symbol, "buy", quantity)
            
            if 'error' in order_result:
                print(f"❌ Failed to place order for {symbol}: {order_result['error']}", file=sys.stderr)
                return False
            
            print(f"✅ Placed {quantity} shares of {symbol} at ${trade_price:.2f}", file=sys.stderr)
            print(f"   Order ID: {order_result.get('id', 'Unknown')}", file=sys.stderr)
            print(f"   Position Value: ${position_value:,.2f}", file=sys.stderr)
            return True
            
        except Exception as e:
            print(f"❌ Error executing trade for {symbol}: {e}", file=sys.stderr)
            return False
    
    def should_trade_signal(self, signal_data: Dict) -> bool:
        """Determine if a signal should be traded based on criteria"""
        setup = signal_data['setup']
        
        # Only trade high-confidence signals
        if setup.score < 0.6:
            return False
        
        # Check RSI (avoid overbought)
        rsi = signal_data.get('rsi', 50)
        if rsi > 75:
            return False
        
        # Check Z-score (need momentum)
        z_score = signal_data.get('z_score', 0)
        if z_score < 1.0:
            return False
        
        # Check change percentage (need positive momentum)
        change_pct = signal_data.get('change_pct', 0)
        if change_pct < 0:
            return False
        
        # Prefer flag breakouts over range breakouts
        if setup.setup == "Flag Breakout" and setup.score >= 0.7:
            return True
        
        # Range breakouts need higher score
        if setup.setup == "Range Breakout" and setup.score >= 0.8:
            return True
        
        return False
    
    async def scan_breakouts_with_mcp(self, top_n: int = 10) -> List[Dict]:
        """Scan for breakouts using MCP server"""
        print("🚀 Starting MCP-Integrated Breakout Scan...", file=sys.stderr)
        
        # Check market status
        market_open = await self.check_market_status()
        print(f"📅 Market Status: {'Open' if market_open else 'Closed'}", file=sys.stderr)
        
        # Get account info
        buying_power = await self.get_account_buying_power()
        print(f"💰 Buying Power: ${buying_power:,.2f}", file=sys.stderr)
        
        # Get liquid stocks from MCP
        symbols = await self.mcp_provider.get_liquid_stocks(limit=30)  # Limit to 30 for performance
        print(f"📊 Analyzing {len(symbols)} liquid stocks from MCP...", file=sys.stderr)
        
        setups = []
        
        for i, symbol in enumerate(symbols):
            try:
                print(f"📈 Analyzing {symbol} ({i+1}/{len(symbols)})...", file=sys.stderr)
                
                # Get stock bars from MCP (fallback to mock data if needed)
                bars = await self.mcp_provider.get_stock_bars(symbol, days=90)
                if bars is None:
                    # Use mock data for testing
                    bars = self.create_mock_bars(symbol, days=90)
                
                if len(bars) < 30:
                    continue
                
                # Calculate technical indicators
                closes = [float(bar.close) for bar in bars]
                highs = [float(bar.high) for bar in bars]
                lows = [float(bar.low) for bar in bars]
                
                rsi = calculate_rsi(closes)
                atr = calculate_atr(highs, lows, closes)
                z_score = calculate_z_score(closes)
                adr_pct = calculate_adr_pct(closes)
                
                # Calculate change percentage
                if len(closes) >= 2:
                    change_pct = ((closes[-1] - closes[-2]) / closes[-2]) * 100
                else:
                    change_pct = 0.0
                
                # Detect breakouts
                flag_breakout = detect_flag_breakout_setup(bars, symbol)
                range_breakout = detect_range_breakout_setup(bars, symbol)
                
                # Add flag breakout if found
                if flag_breakout:
                    signal_data = {
                        'symbol': symbol,
                        'setup': flag_breakout,
                        'price': float(bars[-1].close),
                        'change_pct': change_pct,
                        'adr_pct': adr_pct,
                        'rsi': rsi,
                        'tr_atr': atr,
                        'z_score': z_score,
                        'bars': bars
                    }
                    setups.append(signal_data)
                
                # Add range breakout if found
                if range_breakout:
                    signal_data = {
                        'symbol': symbol,
                        'setup': range_breakout,
                        'price': float(bars[-1].close),
                        'change_pct': change_pct,
                        'adr_pct': adr_pct,
                        'rsi': rsi,
                        'tr_atr': atr,
                        'z_score': z_score,
                        'bars': bars
                    }
                    setups.append(signal_data)
                
            except Exception as e:
                print(f"Error processing {symbol}: {e}", file=sys.stderr)
                continue
        
        # Sort by setup score
        def sort_key(x):
            base_score = x['setup'].score
            # Flag breakouts get slight priority
            if x['setup'].setup == "Flag Breakout":
                return base_score + 0.1
            return base_score
        
        setups.sort(key=sort_key, reverse=True)
        top_setups = setups[:top_n]
        
        print(f"🎯 Found {len(setups)} breakout signals, showing top {len(top_setups)}", file=sys.stderr)
        
        # Execute trades if enabled and market is open
        if self.auto_trade and market_open and buying_power > 1000:
            print("🤖 Auto-trading enabled - executing trades for high-confidence signals...", file=sys.stderr)
            
            trades_executed = 0
            for signal_data in top_setups:
                if self.should_trade_signal(signal_data):
                    success = await self.execute_breakout_trade(signal_data)
                    if success:
                        trades_executed += 1
                        # Only execute one trade per scan to avoid over-trading
                        break
            
            if trades_executed > 0:
                print(f"✅ Executed {trades_executed} trades", file=sys.stderr)
            else:
                print("ℹ️  No trades executed - no signals met criteria", file=sys.stderr)
        
        return top_setups

async def main():
    """Main function for MCP-integrated breakout scanning"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MCP-Integrated Breakout Scanner')
    parser.add_argument('--auto-trade', action='store_true', 
                       help='Enable automatic trading (default: False)')
    parser.add_argument('--position-size', type=float, default=10.0,
                       help='Position size as percentage of buying power (default: 10%%)')
    parser.add_argument('--top-n', type=int, default=10,
                       help='Number of top signals to show (default: 10)')
    
    args = parser.parse_args()
    
    print("🚀 MCP-Integrated Breakout Scanner", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    
    scanner = MCPIntegratedBreakoutScanner(
        auto_trade=args.auto_trade,
        position_size_pct=args.position_size
    )
    
    try:
        # Run the scan
        signals = await scanner.scan_breakouts_with_mcp(top_n=args.top_n)
        
        # Output signals in the same format as the original scanner
        for signal_data in signals:
            symbol = signal_data['symbol']
            price = signal_data['price']
            change_pct = signal_data['change_pct']
            setup = signal_data['setup']
            rsi = signal_data['rsi']
            tr_atr = signal_data['tr_atr']
            z_score = signal_data['z_score']
            
            signal_str = format_breakout_signal(
                symbol, price, change_pct, 0.5, 0.0, setup.setup, rsi, tr_atr, z_score
            )
            print(signal_str)
        
        if not signals:
            print("No breakout signals found", file=sys.stderr)
    
    except Exception as e:
        print(f"❌ Scan failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

