#!/usr/bin/env python3
"""
MCP-Enhanced Breakout Scanner
Integrates Alpaca MCP server capabilities with the existing breakout analysis system
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add the parent directory to the path to import existing modules
sys.path.append(str(Path(__file__).parent.parent))

from breakout_scanner import BreakoutScanner
from breakout_analysis import get_liquid_stocks

class MCPEnhancedScanner(BreakoutScanner):
    """Enhanced breakout scanner with MCP server integration"""
    
    def __init__(self):
        super().__init__()
        self.mcp_server_path = Path(__file__).parent.parent.parent / "alpaca-mcp-server"
        self.api_key = None
        self.secret_key = None
        
        # Load API keys from existing config
        self._load_api_keys()
    
    def _load_api_keys(self):
        """Load API keys from existing configuration"""
        config_path = Path(__file__).parent.parent / "config" / "api_keys.env"
        
        if config_path.exists():
            with open(config_path) as f:
                for line in f:
                    if line.startswith('ALPACA_API_KEY='):
                        self.api_key = line.split('=', 1)[1].strip()
                    elif line.startswith('ALPACA_SECRET_KEY='):
                        self.secret_key = line.split('=', 1)[1].strip()
        
        if not self.api_key or not self.secret_key:
            print("⚠️  Warning: Alpaca API keys not found. MCP features will be disabled.")
    
    async def _call_mcp_tool(self, tool_name: str, arguments: Dict = None) -> Dict:
        """Call an MCP tool via subprocess"""
        if not self.api_key or not self.secret_key:
            return {"error": "API keys not configured"}
        
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
                return json.loads(result.stdout)
            else:
                return {"error": result.stderr or "No output"}
                
        except Exception as e:
            return {"error": str(e)}
        finally:
            if script_path.exists():
                script_path.unlink()
    
    async def get_account_status(self) -> Dict:
        """Get account status using MCP server"""
        return await self._call_mcp_tool("get_account_info")
    
    async def check_market_status(self) -> Dict:
        """Check market status using MCP server"""
        return await self._call_mcp_tool("get_market_clock")
    
    async def get_current_quote(self, symbol: str) -> Dict:
        """Get current quote using MCP server"""
        return await self._call_mcp_tool("get_stock_quote", {"symbol": symbol})
    
    async def execute_breakout_trade(self, symbol: str, signal_data: Dict) -> bool:
        """Execute a trade based on breakout signal"""
        try:
            # Check market status first
            market_status = await self.check_market_status()
            if not market_status.get('is_open', False):
                print(f"🚫 Market is closed, skipping trade for {symbol}")
                return False
            
            # Get account info
            account_info = await self.get_account_status()
            buying_power = float(account_info.get('buying_power', 0))
            
            if buying_power < 1000:
                print(f"💰 Insufficient buying power: ${buying_power}")
                return False
            
            # Get current quote
            quote = await self.get_current_quote(symbol)
            current_price = float(quote.get('last_price', 0))
            
            if current_price <= 0:
                print(f"❌ Invalid price for {symbol}: ${current_price}")
                return False
            
            # Calculate position size (10% of buying power)
            position_value = buying_power * 0.10
            quantity = int(position_value / current_price)
            
            if quantity < 1:
                print(f"📊 Position size too small for {symbol}")
                return False
            
            # Place market order
            order_args = {
                "symbol": symbol,
                "side": "buy",
                "quantity": quantity,
                "order_type": "market"
            }
            
            order_result = await self._call_mcp_tool("place_stock_order", order_args)
            
            if 'error' not in order_result:
                print(f"✅ Placed {quantity} shares of {symbol} at ${current_price}")
                print(f"   Order ID: {order_result.get('id', 'Unknown')}")
                print(f"   Signal Strength: {signal_data.get('strength', 'Unknown')}")
                return True
            else:
                print(f"❌ Failed to place order for {symbol}: {order_result.get('error')}")
                return False
                
        except Exception as e:
            print(f"❌ Error executing breakout trade: {e}")
            return False
    
    async def enhanced_scan(self, execute_trades: bool = False) -> List[Dict]:
        """Enhanced scan with MCP server integration"""
        print("🚀 Starting MCP-Enhanced Breakout Scan...")
        
        # Check market status
        market_status = await self.check_market_status()
        print(f"📅 Market Status: {'Open' if market_status.get('is_open') else 'Closed'}")
        
        # Get account status
        account_info = await self.get_account_status()
        print(f"💰 Buying Power: ${account_info.get('buying_power', 0)}")
        
        # Run the standard breakout scan
        signals = self.scan_breakouts()
        
        if execute_trades and market_status.get('is_open', False):
            print("\n🎯 Executing trades for high-confidence signals...")
            
            for signal in signals:
                # Only trade high-confidence signals (RSI > 60, Z-score > 1.5)
                if (signal.get('rsi', 0) > 60 and 
                    signal.get('z_score', 0) > 1.5 and
                    signal.get('change_percent', 0) > 0):
                    
                    success = await self.execute_breakout_trade(signal['symbol'], signal)
                    if success:
                        print(f"✅ Trade executed for {signal['symbol']}")
                    else:
                        print(f"❌ Trade failed for {signal['symbol']}")
        
        return signals

async def main():
    """Main function for testing"""
    print("🚀 MCP-Enhanced Breakout Scanner Test")
    print("=" * 50)
    
    scanner = MCPEnhancedScanner()
    
    # Test MCP connection
    print("\n📡 Testing MCP server connection...")
    account_info = await scanner.get_account_status()
    
    if 'error' in account_info:
        print(f"❌ MCP connection failed: {account_info['error']}")
        return
    
    print(f"✅ Connected to Alpaca account")
    print(f"   Account: {account_info.get('account_number', 'Unknown')}")
    print(f"   Buying Power: ${account_info.get('buying_power', 0)}")
    
    # Run enhanced scan
    print("\n🔍 Running enhanced breakout scan...")
    signals = await scanner.enhanced_scan(execute_trades=False)  # Set to True to execute trades
    
    print(f"\n📊 Found {len(signals)} breakout signals")
    for signal in signals[:5]:  # Show first 5
        print(f"   {signal['symbol']}: {signal['change_percent']:.1f}% | RSI {signal['rsi']:.0f} | Z {signal['z_score']:.1f}")

if __name__ == "__main__":
    asyncio.run(main())

