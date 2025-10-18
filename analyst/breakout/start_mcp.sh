#!/bin/bash
# Start MCP-Enhanced Breakout Analyst

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASYMMETRIC_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo "🚀 Starting MCP-Enhanced Breakout Analyst..."
echo "============================================="

# Check if already running
if pgrep -f "mcp_breakout_analyst.sh" > /dev/null; then
    echo "❌ MCP Breakout Analyst is already running"
    echo "   Use ./stop_mcp.sh to stop it first"
    exit 1
fi

# Start the analyst in the background
cd "$SCRIPT_DIR"
nohup ./mcp_breakout_analyst.sh > /dev/null 2>&1 &

echo "✅ MCP Breakout Analyst started in background"
echo "📊 Monitoring breakout signals with MCP integration"
echo "📧 Email notifications: deniz@bora.box"
echo ""
echo "📋 To monitor:"
echo "   tail -f logs/mcp_breakout_analyst.log"
echo ""
echo "🛑 To stop:"
echo "   ./stop_mcp.sh"

