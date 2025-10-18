# Alpaca MCP Server Integration Guide

## Overview

This guide explains how to use the Alpaca MCP (Model Context Protocol) server with your existing asymmetric trading system. The MCP server provides natural language access to Alpaca's trading API through AI assistants like Claude, Cursor, and VS Code.

## What's Been Set Up

### 1. MCP Server Installation
- ✅ Cloned the official Alpaca MCP server repository
- ✅ Installed dependencies in a virtual environment
- ✅ Configured with your existing API keys
- ✅ Created integration modules for your breakout analysis system

### 2. Available Tools
The MCP server provides 31+ tools for trading operations:

**Account & Portfolio:**
- `get_account_info()` - View balance, buying power, account status
- `get_positions()` - List all current positions
- `close_position(symbol, percentage)` - Close positions

**Market Data:**
- `get_stock_quote(symbol)` - Real-time quotes
- `get_stock_bars(symbol, days, timeframe)` - Historical data
- `get_market_clock()` - Market open/close status

**Trading:**
- `place_stock_order(symbol, side, quantity, order_type)` - Place orders
- `cancel_order_by_id(order_id)` - Cancel orders
- `cancel_all_orders()` - Cancel all orders

## Usage Options

### Option 1: Direct Integration (Recommended)
Use the enhanced scanner that integrates MCP server capabilities:

```bash
cd /Users/deniz/Code/asymmetric
python analyst/breakout/mcp_enhanced_scanner.py
```

This provides:
- Market status checking
- Account balance monitoring
- Automatic trade execution for high-confidence signals
- Integration with your existing breakout analysis

### Option 2: MCP Client Configuration
Configure Cursor to use the MCP server directly:

**For Cursor:**
1. Create or edit `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "alpaca": {
      "type": "stdio",
      "command": "/Users/deniz/Code/asymmetric/analyst/alpaca/venv/bin/python",
      "args": [
        "/Users/deniz/Code/asymmetric/analyst/alpaca/alpaca_mcp_server.py"
      ],
      "env": {
        "ALPACA_API_KEY": "PK5KN56VW1TVTL7X2GSJ",
        "ALPACA_SECRET_KEY": "Ojsiz7lO4SgTHRLLHz2nYxEoitOaKL1sOmGXAcz3",
        "ALPACA_PAPER_TRADE": "True"
      }
    }
  }
}
```

2. Restart Cursor
3. Use natural language commands like:
   - "What's my current account balance?"
   - "Show me my positions"
   - "Buy 10 shares of AAPL at market price"
   - "What's the current quote for TSLA?"

### Option 3: HTTP Transport (Remote Access)
For running the server on a remote machine:

```bash
cd /Users/deniz/Code/asymmetric/analyst/alpaca
source venv/bin/activate
python alpaca_mcp_server.py --transport http --host 0.0.0.0 --port 8000
```

## Integration with Existing System

### Enhanced Breakout Scanner
The `mcp_enhanced_scanner.py` extends your existing breakout analysis with:

1. **Market Status Checking**: Only trades when markets are open
2. **Account Monitoring**: Checks buying power before placing trades
3. **Real-time Quotes**: Gets current prices for accurate trade sizing
4. **Automated Execution**: Places trades for high-confidence signals
5. **Risk Management**: 10% position sizing with minimum buying power checks

### Key Features
- **Paper Trading**: All trades are in paper mode by default
- **Signal Filtering**: Only executes trades for strong signals (RSI > 60, Z-score > 1.5)
- **Position Sizing**: Uses 10% of buying power per position
- **Error Handling**: Comprehensive error handling and logging

## Example Usage

### Basic Account Check
```python
from analyst.breakout.mcp_enhanced_scanner import MCPEnhancedScanner

scanner = MCPEnhancedScanner()
account_info = await scanner.get_account_status()
print(f"Buying Power: ${account_info.get('buying_power', 0)}")
```

### Run Enhanced Scan with Trading
```python
# Scan for breakouts and execute trades
signals = await scanner.enhanced_scan(execute_trades=True)
```

### Natural Language Queries (via Cursor)
Once configured, you can ask:
- "What's my current buying power?"
- "Show me all my open positions"
- "Place a market order to buy 5 shares of AAPL"
- "Cancel all my open orders"
- "What's the current market status?"

## Security Notes

1. **Paper Trading**: The system is configured for paper trading by default
2. **API Keys**: Your existing API keys are used securely
3. **Risk Management**: Built-in position sizing and buying power checks
4. **Review Required**: Always review trades before execution in live mode

## Troubleshooting

### Common Issues

1. **"API keys not found"**
   - Ensure `analyst/config/api_keys.env` exists and has correct keys

2. **"MCP connection failed"**
   - Check that the virtual environment is properly set up
   - Verify API keys are correct

3. **"Market is closed"**
   - Normal behavior - trading only occurs during market hours

### Debug Mode
Enable debug mode by setting `DEBUG=True` in the MCP server configuration.

## Next Steps

1. **Test the Integration**: Run the enhanced scanner to verify everything works
2. **Configure Cursor**: Set up the MCP client configuration for natural language access
3. **Monitor Performance**: Use the enhanced scanner alongside your existing system
4. **Customize Trading Logic**: Modify the signal filtering and position sizing as needed

## Files Created

- `analyst/alpaca/` - Official Alpaca MCP server installation (relocated)
- `alpaca_mcp_integration.py` - Full async integration module
- `mcp_trader.py` - Simple MCP trader interface
- `analyst/breakout/mcp_enhanced_scanner.py` - Enhanced scanner with MCP integration
- `test_mcp_client.py` - Test script for MCP functionality
- `MCP_INTEGRATION_GUIDE.md` - This guide

The MCP server integration provides a powerful bridge between your automated trading system and natural language AI assistants, enabling both programmatic and conversational access to your Alpaca trading account.
