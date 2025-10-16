#!/bin/bash
# Start Analyst Mode - Market Analysis & Signal Generation
# Schedule: 8 AM - 5 PM Eastern Time

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYST_SCRIPT="$SCRIPT_DIR/analyst/analyst.sh"

echo "🚀 Starting Analyst Mode..."
echo "📊 Market Analysis & Signal Generation"
echo "⏰ Schedule: 8 AM - 5 PM Eastern Time"
echo ""

# Make sure the analyst script is executable
chmod +x "$ANALYST_SCRIPT"

# Check if already running
if pgrep -f "analyst.sh" > /dev/null; then
    echo "⚠️  Analyst is already running"
    exit 1
fi

# Start analyst in background
nohup "$ANALYST_SCRIPT" > /dev/null 2>&1 &
ANALYST_PID=$!

echo "✅ Analyst started (PID: $ANALYST_PID)"
echo "📝 Logs: $SCRIPT_DIR/analyst/logs/analyst.log"
echo ""
echo "To check status: ./status.sh"
echo "To stop: ./stop_analyst.sh"
