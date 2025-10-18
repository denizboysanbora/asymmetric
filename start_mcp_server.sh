#!/bin/bash
# Start Alpaca MCP Server
# This script starts the MCP server with your configured API keys

echo "🚀 Starting Alpaca MCP Server..."
echo "=================================="

# Change to the MCP server directory
cd "$(dirname "$0")/alpaca-mcp-server"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first."
    exit 1
fi

# Load API keys from existing config
ASYMMETRIC_DIR="$(dirname "$0")"
if [ -f "$ASYMMETRIC_DIR/analysts/config/api_keys.env" ]; then
    source "$ASYMMETRIC_DIR/analysts/config/api_keys.env"
    echo "✅ Loaded API keys from existing config"
else
    echo "❌ API keys not found in analysts/config/api_keys.env"
    exit 1
fi

# Set environment variables
export ALPACA_API_KEY="$ALPACA_API_KEY"
export ALPACA_SECRET_KEY="$ALPACA_SECRET_KEY"
export ALPACA_PAPER_TRADE="True"

echo "📡 API Key: ${ALPACA_API_KEY:0:8}..."
echo "🔒 Paper Trading: Enabled"
echo ""

# Start the MCP server
echo "🌐 Starting server on stdio transport..."
echo "   Press Ctrl+C to stop"
echo ""

source venv/bin/activate
python alpaca_mcp_server.py

