#!/bin/bash
# Start Qullamaggie Mode - Momentum Pattern Analysis
# Schedule: 8 AM - 4 PM Eastern Time

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QULLAMAGGIE_SCRIPT="$SCRIPT_DIR/qullamaggie.sh"

echo "🚀 Starting Qullamaggie Mode..."
echo "📊 Momentum Pattern Analysis & Watchlist Generation"
echo "⏰ Schedule: 8 AM - 4 PM Eastern Time (every 30 minutes)"
echo "📧 Email notifications only (no tweets)"
echo "🔄 Automatic cron scheduling enabled"
echo ""

# Make sure the qullamaggie script is executable
chmod +x "$QULLAMAGGIE_SCRIPT"

# Check if already running
if pgrep -f "qullamaggie.sh" > /dev/null; then
    echo "⚠️  Qullamaggie is already running"
    exit 1
fi

# Start qullamaggie in background
nohup "$QULLAMAGGIE_SCRIPT" > /dev/null 2>&1 &
QULLAMAGGIE_PID=$!

echo "✅ Qullamaggie started (PID: $QULLAMAGGIE_PID)"
echo "📝 Logs: $SCRIPT_DIR/logs/qullamaggie.log"
echo ""
echo "To check status: ./status.sh"
echo "To stop: ./stop.sh"