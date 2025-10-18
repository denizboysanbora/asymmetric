#!/bin/bash
# Stop MCP-Enhanced Breakout Analyst

echo "🛑 Stopping MCP-Enhanced Breakout Analyst..."

# Kill the analyst process
if pgrep -f "mcp_breakout_analyst.sh" > /dev/null; then
    pkill -f "mcp_breakout_analyst.sh"
    echo "✅ MCP Breakout Analyst stopped"
else
    echo "ℹ️  MCP Breakout Analyst was not running"
fi

# Clean up lock file
LOCK_FILE="/tmp/mcp_breakout_analyst.lock"
if [ -f "$LOCK_FILE" ]; then
    rm -f "$LOCK_FILE"
    echo "🧹 Cleaned up lock file"
fi

