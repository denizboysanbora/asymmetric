#!/bin/bash
# Start the automated scanner, tweeter, and emailer v2.0
# Stocks on weekdays, crypto on weekends, every 25 minutes

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ALPACA_DIR="$SCRIPT_DIR/alpaca/alpaca-mcp-server"
LOG_FILE="$SCRIPT_DIR/auto_scan_tweet.log"
PID_FILE="$SCRIPT_DIR/auto_scan_tweet.pid"

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "Auto-trader is already running (PID: $OLD_PID)"
        echo "To stop it, run: kill $OLD_PID"
        exit 1
    else
        echo "Removing stale PID file..."
        rm "$PID_FILE"
    fi
fi

# Check for Alpaca credentials
if ! grep -q "your_alpaca_api_key_here" "$ALPACA_DIR/.env" 2>/dev/null; then
    echo "Starting auto-scanner v2.0..."
    echo "  • Weekdays: Stocks (10 AM - 4 PM ET)"
    echo "  • Weekends: Crypto (24/7)"
    echo "  • Interval: Every 25 minutes"
    echo "  • Actions: Tweet + Email + Save to DB"
else
    echo "⚠️  WARNING: Alpaca API keys not configured!"
    echo "Edit: $ALPACA_DIR/.env"
    echo ""
    echo "Starting anyway (will fail without valid keys)..."
fi

# Start the scanner in background
cd "$ALPACA_DIR"
nohup ./venv/bin/python3 auto_scan_tweet_v2.py > "$LOG_FILE" 2>&1 &
PID=$!

# Save PID
echo $PID > "$PID_FILE"

echo "✅ Auto-trader v2.0 started!"
echo "   PID: $PID"
echo "   Log: $LOG_FILE"
echo ""
echo "To view logs: tail -f $LOG_FILE"
echo "To stop: kill $PID  (or run: kill \$(cat $PID_FILE))"

