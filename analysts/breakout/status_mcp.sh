#!/bin/bash
# Check status of MCP-Enhanced Breakout Analyst

echo "📊 MCP-Enhanced Breakout Analyst Status"
echo "======================================="

# Check if running
if pgrep -f "mcp_breakout_analyst.sh" > /dev/null; then
    echo "✅ Status: Running"
    echo "📅 Started: $(ps -o lstart= -p $(pgrep -f "mcp_breakout_analyst.sh"))"
else
    echo "❌ Status: Not running"
fi

# Check lock file
LOCK_FILE="/tmp/mcp_breakout_analyst.lock"
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "🔒 Lock file exists (PID: $PID)"
    else
        echo "⚠️  Stale lock file exists"
    fi
else
    echo "🔓 No lock file"
fi

# Check log file
LOG_FILE="logs/mcp_breakout_analyst.log"
if [ -f "$LOG_FILE" ]; then
    echo "📝 Log file: $LOG_FILE"
    echo "📏 Size: $(du -h "$LOG_FILE" | cut -f1)"
    echo "🕒 Last activity: $(tail -1 "$LOG_FILE" | cut -d']' -f1 | tr -d '[')"
else
    echo "📝 No log file found"
fi

# Check MCP server
echo ""
echo "🔧 MCP Server Status:"
MCP_SERVER_PATH="../../alpaca-mcp-server"
if [ -d "$MCP_SERVER_PATH" ]; then
    echo "✅ MCP Server: Installed"
    
    # Check if virtual environment exists
    if [ -d "$MCP_SERVER_PATH/venv" ]; then
        echo "✅ Virtual Environment: Ready"
    else
        echo "❌ Virtual Environment: Missing"
    fi
    
    # Test MCP server
    if [ -f "$MCP_SERVER_PATH/venv/bin/python" ]; then
        echo "✅ Python: Available"
    else
        echo "❌ Python: Missing"
    fi
else
    echo "❌ MCP Server: Not installed"
fi

echo ""
echo "🎯 Quick Actions:"
echo "   Start: ./start_mcp.sh"
echo "   Stop:  ./stop_mcp.sh"
echo "   Logs:  tail -f logs/mcp_breakout_analyst.log"

