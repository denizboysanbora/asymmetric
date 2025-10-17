#!/bin/bash
# Check status of Breakout Analyst

set -euo pipefail

echo "📊 Breakout Analyst Status"
echo "========================="
echo ""

# Check Breakout Analyst Mode
echo "🔍 BREAKOUT ANALYST (Unified Flag + Range Scanner)"
echo "-------------------------------------------------"
BREAKOUT_ANALYST_PIDS=$(pgrep -f "breakout_analyst.sh" || true)
if [ -n "$BREAKOUT_ANALYST_PIDS" ]; then
    echo "✅ Status: RUNNING (PID: $BREAKOUT_ANALYST_PIDS)"
    echo "📝 Logs: $(pwd)/logs/breakout_analyst.log"
    
    # Show recent log entries
    if [ -f "logs/breakout_analyst.log" ]; then
        echo "📋 Recent activity:"
        tail -3 "logs/breakout_analyst.log" | sed 's/^/   /'
    fi
else
    echo "❌ Status: STOPPED"
fi
echo ""

# Check current time and operating hours
echo "⏰ TIME & SCHEDULE"
echo "------------------"
CURRENT_TIME=$(TZ='America/New_York' date '+%Y-%m-%d %H:%M:%S %Z')
CURRENT_HOUR=$(TZ='America/New_York' date '+%H')

echo "Current time: $CURRENT_TIME"
if [ "$CURRENT_HOUR" -ge 10 ] && [ "$CURRENT_HOUR" -lt 16 ]; then
    echo "✅ Within operating hours (10 AM - 4 PM ET)"
else
    echo "❌ Outside operating hours (10 AM - 4 PM ET)"
fi
echo ""

# Check API credentials
echo "🔑 API CREDENTIALS"
echo "-----------------"
if [ -f "../../input/alpaca/.env" ]; then
    echo "✅ Alpaca API: Configured"
else
    echo "❌ Alpaca API: Not configured"
fi

if [ -f "../../output/gmail/token.json" ]; then
    echo "✅ Gmail API: Configured"
else
    echo "❌ Gmail API: Not configured"
fi
echo ""

echo "🎯 DETECTION STRATEGIES"
echo "----------------------"
echo "📈 Flag Breakout: Prior impulse + tight consolidation + higher lows"
echo "📊 Range Breakout: Range-bound trading + breakout above range"
echo "🏆 Priority: Flag breakouts get slight priority over range breakouts"
echo ""

echo "🎯 QUICK COMMANDS"
echo "----------------"
echo "Start Breakout Analyst:  ./start.sh"
echo "Stop Breakout Analyst:   ./stop.sh"
echo "View Logs:               tail -f logs/breakout_analyst.log"