#!/bin/bash
# Start Breakout Analyst - Unified Breakout Scanner
# Schedule: 10 AM - 4 PM Eastern Time

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BREAKOUT_ANALYST_SCRIPT="$SCRIPT_DIR/breakout_analyst.sh"

echo "🚀 Starting Breakout Analyst..."
echo "📊 Unified Breakout Scanner (Flag + Range)"
echo "⏰ Schedule: 10 AM - 4 PM Eastern Time"
echo ""

# Make sure the breakout analyst script is executable
chmod +x "$BREAKOUT_ANALYST_SCRIPT"

# Check if already running
if pgrep -f "breakout_analyst.sh" > /dev/null; then
    echo "⚠️  Breakout analyst is already running"
    exit 1
fi

# Start breakout analyst in background
nohup "$BREAKOUT_ANALYST_SCRIPT" > /dev/null 2>&1 &
BREAKOUT_ANALYST_PID=$!

echo "✅ Breakout analyst started (PID: $BREAKOUT_ANALYST_PID)"
echo "📝 Logs: $SCRIPT_DIR/logs/breakout_analyst.log"
echo ""
echo "To check status: ./status.sh"
echo "To stop: ./stop.sh"