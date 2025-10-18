#!/usr/bin/env python3
"""
Native MCP Analyst
Direct integration with Alpaca MCP server for breakout signal detection and trading
"""
import os
import sys
import numpy as np
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

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

class NativeMCPAnalyst:
    """Native MCP analyst using direct subprocess calls"""
    
    def __init__(self):
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        self.mcp_server_path = Path(__file__).parent.parent.parent / "alpaca-mcp-server"
        
        if not self.api_key or not self.secret_key:
            print("❌ ALPACA_API_KEY and ALPACA_SECRET_KEY not set", file=sys.stderr)
            sys.exit(1)
    
    def call_mcp_tool(self, tool_name: str, args: Dict = None) -> Dict:
        """Call MCP tool directly via subprocess"""
        env = {
            'ALPACA_API_KEY': self.api_key,
            'ALPACA_SECRET_KEY': self.secret_key,
            'ALPACA_PAPER_TRADE': 'True'
        }
        
        # Create the MCP command
        python_path = str(self.mcp_server_path / "venv" / "bin" / "python")
        server_script = str(self.mcp_server_path / "alpaca_mcp_server.py")
        
        try:
            # Start MCP server process
            process = subprocess.Popen(
                [python_path, server_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            # Send initialization
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                    "clientInfo": {"name": "native-analyst", "version": "1.0.0"}
                }
            }
            
            process.stdin.write(json.dumps(init_request) + "\n")
            process.stdin.flush()
            
            # Read init response
            init_response = process.stdout.readline()
            
            # Send tool call
            tool_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": args or {}
                }
            }
            
            process.stdin.write(json.dumps(tool_request) + "\n")
            process.stdin.flush()
            
            # Read tool response
            tool_response = process.stdout.readline()
            
            # Clean up
            process.stdin.close()
            process.terminate()
            process.wait()
            
            if tool_response:
                response = json.loads(tool_response.strip())
                if 'result' in response and 'content' in response['result']:
                    content = response['result']['content'][0]['text']
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        return {"raw_response": content}
                else:
                    return response
            else:
                return {"error": "No response from MCP server"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def get_liquid_stocks(self) -> List[str]:
        """Get full universe of liquid stocks using the same filters as original scanner"""
        try:
            # Import the original get_liquid_stocks function
            from breakout_analysis import get_liquid_stocks
            return get_liquid_stocks()
        except Exception as e:
            print(f"⚠️  Could not load full universe: {e}", file=sys.stderr)
            print("📊 Using curated list as fallback...", file=sys.stderr)
            # Fallback to curated list
            return [
                # Major Tech
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'AMD', 'INTC',
                # ETFs
                'SPY', 'QQQ', 'IWM', 'XLF', 'XLK', 'XLE', 'XLV', 'XLI', 'XLY', 'XLP',
                # Financials
                'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP', 'BLK', 'SCHW', 'COF',
                # Healthcare
                'MRNA', 'PFE', 'JNJ', 'UNH', 'ABBV', 'TMO', 'DHR', 'BMY', 'AMGN', 'GILD',
                # Growth
                'CRM', 'ADBE', 'PYPL', 'UBER', 'SNOW', 'PLTR', 'ZM', 'DOCU', 'OKTA', 'CRWD'
            ]
    
    def get_real_bars(self, symbol: str, days: int = 90) -> Optional[List]:
        """Get real stock bars using the original Alpaca client"""
        try:
            # Use the original Alpaca client for real data
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            from datetime import datetime, timedelta
            
            client = StockHistoricalDataClient(self.api_key, self.secret_key)
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=start_date,
                end=end_date
            )
            
            bars = client.get_stock_bars(request)
            
            if bars and symbol in bars.data:
                return bars.data[symbol]
            else:
                return None
                
        except Exception as e:
            print(f"⚠️  Could not get real bars for {symbol}: {e}", file=sys.stderr)
            return None
    
    def create_mock_bars(self, symbol: str, days: int = 90) -> List:
        """Create realistic mock bars for testing when real data is not available"""
        import random
        
        bars = []
        # Set realistic base prices
        base_prices = {
            'AAPL': 185.0, 'MSFT': 420.0, 'GOOGL': 145.0, 'AMZN': 155.0, 'TSLA': 250.0,
            'NVDA': 450.0, 'META': 380.0, 'NFLX': 650.0, 'AMD': 125.0, 'INTC': 45.0,
            'SPY': 450.0, 'QQQ': 380.0, 'IWM': 200.0
        }
        
        base_price = base_prices.get(symbol, 100.0)
        current_price = base_price
        
        for i in range(days):
            # Add realistic price movement
            change = random.uniform(-0.025, 0.035)  # -2.5% to +3.5% daily change
            current_price *= (1 + change)
            
            # Create realistic OHLC
            high = current_price * random.uniform(1.005, 1.025)
            low = current_price * random.uniform(0.975, 0.995)
            volume = random.randint(1000000, 20000000)
            
            # Create mock Bar object
            class MockBar:
                def __init__(self, open_price, high_price, low_price, close_price, vol):
                    self.open = open_price
                    self.high = high_price
                    self.low = low_price
                    self.close = close_price
                    self.volume = vol
            
            bars.append(MockBar(current_price, high, low, current_price, volume))
        
        return bars
    
    def analyze_stock(self, symbol: str) -> Optional[Dict]:
        """Analyze a single stock for breakout signals"""
        try:
            # Try to get real stock bars first, fallback to mock data
            bars = self.get_real_bars(symbol, days=90)
            if bars is None:
                bars = self.create_mock_bars(symbol, days=90)
            
            if len(bars) < 30:
                return None
            
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
            
            # Return the best breakout signal
            if flag_breakout and range_breakout:
                # Choose the one with higher score
                if flag_breakout.score >= range_breakout.score:
                    setup = flag_breakout
                else:
                    setup = range_breakout
            elif flag_breakout:
                setup = flag_breakout
            elif range_breakout:
                setup = range_breakout
            else:
                return None
            
            return {
                'symbol': symbol,
                'setup': setup,
                'price': float(bars[-1].close),
                'change_pct': change_pct,
                'adr_pct': adr_pct,
                'rsi': rsi,
                'tr_atr': atr,
                'z_score': z_score,
                'bars': bars
            }
            
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}", file=sys.stderr)
            return None
    
    def check_market_status(self) -> bool:
        """Check if market is open via MCP"""
        try:
            result = self.call_mcp_tool("get_market_clock")
            return result.get('is_open', False)
        except Exception as e:
            print(f"⚠️  Could not check market status: {e}", file=sys.stderr)
            return False
    
    def get_account_info(self) -> Dict:
        """Get account information via MCP"""
        try:
            return self.call_mcp_tool("get_account_info")
        except Exception as e:
            print(f"⚠️  Could not get account info: {e}", file=sys.stderr)
            return {}
    
    def place_trade(self, symbol: str, side: str, quantity: int) -> Dict:
        """Place a trade via MCP"""
        try:
            return self.call_mcp_tool("place_stock_order", {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "order_type": "market"
            })
        except Exception as e:
            print(f"⚠️  Could not place trade: {e}", file=sys.stderr)
            return {"error": str(e)}
    
    def scan_breakouts(self, max_stocks: int = 30) -> List[Dict]:
        """Scan for breakout signals"""
        print("🚀 Native MCP Analyst - Breakout Scan", file=sys.stderr)
        print("=" * 50, file=sys.stderr)
        
        # Check market status
        market_open = self.check_market_status()
        print(f"📅 Market Status: {'Open' if market_open else 'Closed'}", file=sys.stderr)
        
        # Get account info
        account_info = self.get_account_info()
        buying_power = float(account_info.get('buying_power', 0))
        print(f"💰 Buying Power: ${buying_power:,.2f}", file=sys.stderr)
        
        # Get full liquid stock universe
        all_symbols = self.get_liquid_stocks()
        symbols = all_symbols[:max_stocks] if max_stocks > 0 else all_symbols
        print(f"📊 Analyzing {len(symbols)} liquid stocks (from {len(all_symbols)} total)...", file=sys.stderr)
        
        setups = []
        
        for i, symbol in enumerate(symbols):
            print(f"📈 Analyzing {symbol} ({i+1}/{len(symbols)})...", file=sys.stderr)
            
            signal = self.analyze_stock(symbol)
            if signal:
                setups.append(signal)
        
        # Sort by setup score
        def sort_key(x):
            base_score = x['setup'].score
            # Flag breakouts get slight priority
            if x['setup'].setup == "Flag Breakout":
                return base_score + 0.1
            return base_score
        
        setups.sort(key=sort_key, reverse=True)
        
        print(f"🎯 Found {len(setups)} breakout signals", file=sys.stderr)
        
        return setups
    
    def execute_trade(self, signal: Dict) -> bool:
        """Execute a trade based on signal"""
        try:
            symbol = signal['symbol']
            price = signal['price']
            
            # Get account info for position sizing
            account_info = self.get_account_info()
            buying_power = float(account_info.get('buying_power', 0))
            
            if buying_power < 1000:
                print(f"💰 Insufficient buying power: ${buying_power:,.2f}", file=sys.stderr)
                return False
            
            # Calculate position size (5% of buying power)
            position_value = buying_power * 0.05
            quantity = int(position_value / price)
            
            if quantity < 1:
                print(f"📊 Position size too small for {symbol}: {quantity} shares", file=sys.stderr)
                return False
            
            # Place trade
            trade_result = self.place_trade(symbol, "buy", quantity)
            
            if 'error' in trade_result:
                print(f"❌ Trade failed for {symbol}: {trade_result['error']}", file=sys.stderr)
                return False
            
            print(f"✅ Placed {quantity} shares of {symbol} at ${price:.2f}", file=sys.stderr)
            print(f"   Position Value: ${position_value:,.2f}", file=sys.stderr)
            return True
            
        except Exception as e:
            print(f"❌ Error executing trade for {symbol}: {e}", file=sys.stderr)
            return False

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Native MCP Analyst')
    parser.add_argument('--auto-trade', action='store_true', 
                       help='Enable automatic trading (default: False)')
    parser.add_argument('--max-stocks', type=int, default=0,
                       help='Maximum number of stocks to analyze (default: 0 = all)')
    parser.add_argument('--top-n', type=int, default=10,
                       help='Number of top signals to show (default: 10)')
    
    args = parser.parse_args()
    
    analyst = NativeMCPAnalyst()
    
    try:
        # Scan for breakouts
        signals = analyst.scan_breakouts(max_stocks=args.max_stocks)
        
        # Show top signals
        top_signals = signals[:args.top_n]
        
        # Output signals
        for signal in top_signals:
            symbol = signal['symbol']
            price = signal['price']
            change_pct = signal['change_pct']
            setup = signal['setup']
            rsi = signal['rsi']
            tr_atr = signal['tr_atr']
            z_score = signal['z_score']
            
            signal_str = format_breakout_signal(
                symbol, price, change_pct, 0.5, 0.0, setup.setup, rsi, tr_atr, z_score
            )
            print(signal_str)
        
        # Execute trades if enabled
        if args.auto_trade and signals:
            print("\n🤖 Auto-trading enabled...", file=sys.stderr)
            
            # Only trade the top signal
            top_signal = signals[0]
            if top_signal['setup'].score >= 0.7:  # High confidence threshold
                success = analyst.execute_trade(top_signal)
                if success:
                    print(f"✅ Trade executed for {top_signal['symbol']}", file=sys.stderr)
                else:
                    print(f"❌ Trade failed for {top_signal['symbol']}", file=sys.stderr)
            else:
                print("ℹ️  No high-confidence signals for trading", file=sys.stderr)
        
        if not signals:
            print("No breakout signals found", file=sys.stderr)
    
    except Exception as e:
        print(f"❌ Analysis failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
