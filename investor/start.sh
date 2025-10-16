#!/bin/bash
# Start Investor Mode - Trading Execution & Portfolio Management
# Schedule: 8 AM - 5 PM Eastern Time

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INVESTOR_SCRIPT="$SCRIPT_DIR/investor.sh"

echo "🚀 Starting Investor Mode..."
echo "💰 Trading Execution & Portfolio Management"
echo "⏰ Schedule: 8 AM - 5 PM Eastern Time"
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
echo "To stop: ./stop_investor.sh"
