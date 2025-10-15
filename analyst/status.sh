#!/bin/bash
# Check status of the auto-trading system

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/auto_scan_tweet.pid"
LOG_FILE="$SCRIPT_DIR/auto_scan_tweet.log"

echo "========================================================================"
echo "📊 Auto-Trading System v2.0 Status"
echo "========================================================================"
echo "Schedule:"
echo "  • Weekdays (Mon-Fri): Stocks every 25 min (10 AM - 4 PM ET)"
echo "  • Weekends (Sat-Sun): Crypto every 25 min (24/7)"
echo "  • Actions: Tweet + Email + Database"
echo ""

# Check if running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ Status: RUNNING (PID: $PID)"
        echo ""
        echo "Last 10 log entries:"
        echo "------------------------------------------------------------------------"
        tail -10 "$LOG_FILE" 2>/dev/null || echo "No logs available"
    else
        echo "❌ Status: NOT RUNNING (stale PID file)"
    fi
else
    echo "❌ Status: NOT RUNNING"
fi

echo ""
echo "========================================================================"
echo "📈 Twitter Rate Limits"
echo "========================================================================"
cd "$SCRIPT_DIR/../output/x"
./check_rate_limits.sh 2>/dev/null || echo "Rate limit check unavailable"

echo ""
echo "========================================================================"
echo "Commands:"
echo "  Start:  ./start_auto_trader.sh"
echo "  Stop:   ./stop_auto_trader.sh"
echo "  Logs:   tail -f $LOG_FILE"
echo "========================================================================"

