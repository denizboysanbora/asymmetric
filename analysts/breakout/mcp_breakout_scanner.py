#!/usr/bin/env python3
"""
MCP-Enhanced Breakout Scanner
Integrates Alpaca MCP server for real-time trading operations with breakout analysis
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
    kristjan_checklist,
    format_breakout_signal,
    SetupTag
)
from breakout_analysis import get_liquid_stocks

# Import Alpaca modules
try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.trading.client import TradingClient
    from alpaca.data.models import Bar
except ImportError as e:
    print(f"Error importing Alpaca modules: {e}", file=sys.stderr)
    sys.exit(1)

class MCPTrader:
    """MCP server integration for trading operations"""
    
    def __init__(self):
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        self.mcp_server_path = Path(__file__).parent.parent.parent / "alpaca-mcp-server"
        
        if not self.api_key or not self.secret_key:
            print("⚠️  Warning: Alpaca API keys not found. MCP trading disabled.", file=sys.stderr)
            self.enabled = False
        else:
            self.enabled = True
    
    async def _call_mcp_tool(self, tool_name: str, arguments: Dict = None) -> Dict:
        """Call an MCP tool via subprocess"""
        if not self.enabled:
            return {"error": "MCP trading disabled - no API keys"}
        
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
    
    async def get_account_info(self) -> Dict:
        """Get account information"""
        return await self._call_mcp_tool("get_account_info")
    
    async def get_market_clock(self) -> Dict:
        """Get market clock information"""
        return await self._call_mcp_tool("get_market_clock")
    
    async def get_stock_quote(self, symbol: str) -> Dict:
        """Get current stock quote"""
        return await self._call_mcp_tool("get_stock_quote", {"symbol": symbol})
    
    async def place_market_order(self, symbol: str, side: str, quantity: int) -> Dict:
        """Place a market order"""
        return await self._call_mcp_tool("place_stock_order", {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "order_type": "market"
        })
    
    async def get_positions(self) -> Dict:
        """Get current positions"""
        return await self._call_mcp_tool("get_positions")
    
    async def close_position(self, symbol: str, percentage: float = 100.0) -> Dict:
        """Close a position by percentage"""
        return await self._call_mcp_tool("close_position", {
            "symbol": symbol,
            "percentage": percentage
        })

class MCPBreakoutScanner:
    """Enhanced breakout scanner with MCP trading integration"""
    
    def __init__(self, auto_trade: bool = False, position_size_pct: float = 10.0):
        self.auto_trade = auto_trade
        self.position_size_pct = position_size_pct
        self.mcp_trader = MCPTrader()
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        if not self.api_key or not self.secret_key:
            print("❌ ALPACA_API_KEY and ALPACA_SECRET_KEY not set", file=sys.stderr)
            sys.exit(1)
        
        self.client = StockHistoricalDataClient(self.api_key, self.secret_key)
    
    async def check_market_status(self) -> bool:
        """Check if market is open"""
        try:
            market_clock = await self.mcp_trader.get_market_clock()
            return market_clock.get('is_open', False)
        except Exception as e:
            print(f"⚠️  Could not check market status: {e}", file=sys.stderr)
            return False
    
    async def get_account_buying_power(self) -> float:
        """Get current buying power"""
        try:
            account_info = await self.mcp_trader.get_account_info()
            return float(account_info.get('buying_power', 0))
        except Exception as e:
            print(f"⚠️  Could not get account info: {e}", file=sys.stderr)
            return 0.0
    
    async def execute_breakout_trade(self, signal_data: Dict) -> bool:
        """Execute a trade based on breakout signal"""
        try:
            symbol = signal_data['symbol']
            current_price = signal_data['price']
            
            # Get current quote for accurate pricing
            quote = await self.mcp_trader.get_stock_quote(symbol)
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
            order_result = await self.mcp_trader.place_market_order(symbol, "buy", quantity)
            
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
    
    async def scan_breakouts_with_trading(self, top_n: int = 10) -> List[Dict]:
        """Scan for breakouts and optionally execute trades"""
        print("🚀 Starting MCP-Enhanced Breakout Scan...", file=sys.stderr)
        
        # Check market status
        market_open = await self.check_market_status()
        print(f"📅 Market Status: {'Open' if market_open else 'Closed'}", file=sys.stderr)
        
        # Get account info
        buying_power = await self.get_account_buying_power()
        print(f"💰 Buying Power: ${buying_power:,.2f}", file=sys.stderr)
        
        # Get liquid stocks (limit to top 50 for performance)
        all_symbols = get_liquid_stocks()
        # Take top 50 most liquid stocks to prevent timeout
        symbols = all_symbols[:50]
        print(f"📊 Analyzing top {len(symbols)} liquid stocks (from {len(all_symbols)} total)...", file=sys.stderr)
        
        setups = []
        
        for symbol in symbols:
            try:
                # Get daily bars for last 3 months
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)
                
                request = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=TimeFrame.Day,
                    start=start_date,
                    end=end_date
                )
                
                bars = self.client.get_stock_bars(request)
                
                if not bars or symbol not in bars.data:
                    continue
                
                symbol_bars = bars.data[symbol]
                if len(symbol_bars) < 30:
                    continue
                
                # Calculate technical indicators
                closes = [float(bar.close) for bar in symbol_bars]
                highs = [float(bar.high) for bar in symbol_bars]
                lows = [float(bar.low) for bar in symbol_bars]
                
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
                flag_breakout = detect_flag_breakout_setup(symbol_bars, symbol)
                range_breakout = detect_range_breakout_setup(symbol_bars, symbol)
                
                # Add flag breakout if found
                if flag_breakout:
                    signal_data = {
                        'symbol': symbol,
                        'setup': flag_breakout,
                        'price': float(symbol_bars[-1].close),
                        'change_pct': change_pct,
                        'adr_pct': adr_pct,
                        'rsi': rsi,
                        'tr_atr': atr,
                        'z_score': z_score,
                        'bars': symbol_bars
                    }
                    setups.append(signal_data)
                
                # Add range breakout if found
                if range_breakout:
                    signal_data = {
                        'symbol': symbol,
                        'setup': range_breakout,
                        'price': float(symbol_bars[-1].close),
                        'change_pct': change_pct,
                        'adr_pct': adr_pct,
                        'rsi': rsi,
                        'tr_atr': atr,
                        'z_score': z_score,
                        'bars': symbol_bars
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
    """Main function for MCP-enhanced breakout scanning"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MCP-Enhanced Breakout Scanner')
    parser.add_argument('--auto-trade', action='store_true', 
                       help='Enable automatic trading (default: False)')
    parser.add_argument('--position-size', type=float, default=10.0,
                       help='Position size as percentage of buying power (default: 10%%)')
    parser.add_argument('--top-n', type=int, default=10,
                       help='Number of top signals to show (default: 10)')
    
    args = parser.parse_args()
    
    print("🚀 MCP-Enhanced Breakout Scanner", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    
    scanner = MCPBreakoutScanner(
        auto_trade=args.auto_trade,
        position_size_pct=args.position_size
    )
    
    try:
        # Run the scan
        signals = await scanner.scan_breakouts_with_trading(top_n=args.top_n)
        
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
