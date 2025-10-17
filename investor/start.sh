#!/bin/bash
# Start Investor Mode - Paper Trading Execution
# Schedule: 10 AM - 4 PM Eastern Time

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INVESTOR_SCRIPT="$SCRIPT_DIR/investor.sh"

echo "🚀 Starting Investor Mode..."
echo "💰 Paper Trading Execution"
echo "⏰ Schedule: 10 AM - 4 PM Eastern Time"
echo ""

# Make sure the investor script is executable
chmod +x "$INVESTOR_SCRIPT"

# Check if already running
if pgrep -f "investor.sh" > /dev/null; then
    echo "⚠️  Investor is already running"
    exit 1
fi

# Start investor in background
nohup "$INVESTOR_SCRIPT" > /dev/null 2>&1 &
INVESTOR_PID=$!

echo "✅ Investor started (PID: $INVESTOR_PID)"
echo "📝 Logs: $SCRIPT_DIR/logs/investor.log"
echo ""
echo "To check status: ./status.sh"
echo "To stop: ./stop.sh"
