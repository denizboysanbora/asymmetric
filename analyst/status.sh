#!/bin/bash
# Check status of both Analyst and Investor modes

set -euo pipefail

echo "📊 Asymmetric Trading System Status"
echo "=================================="
echo ""

# Check Analyst Mode
echo "🔍 ANALYST MODE (Market Analysis & Signal Generation)"
echo "----------------------------------------------------"
ANALYST_PIDS=$(pgrep -f "analyst.sh" || true)
if [ -n "$ANALYST_PIDS" ]; then
    echo "✅ Status: RUNNING (PID: $ANALYST_PIDS)"
    echo "📝 Logs: $(pwd)/analyst/logs/analyst.log"
    
    # Show recent log entries
    if [ -f "analyst/logs/analyst.log" ]; then
        echo "📋 Recent activity:"
        tail -3 "analyst/logs/analyst.log" | sed 's/^/   /'
    fi
else
    echo "❌ Status: STOPPED"
fi
echo ""

# Check Investor Mode
echo "💰 INVESTOR MODE (Trading Execution & Portfolio Management)"
echo "----------------------------------------------------------"
INVESTOR_PIDS=$(pgrep -f "investor.sh" || true)
if [ -n "$INVESTOR_PIDS" ]; then
    echo "✅ Status: RUNNING (PID: $INVESTOR_PIDS)"
    echo "📝 Logs: $(pwd)/investor/logs/investor.log"
    
    # Show recent log entries
    if [ -f "investor/logs/investor.log" ]; then
        echo "📋 Recent activity:"
        tail -3 "investor/logs/investor.log" | sed 's/^/   /'
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
if [ "$CURRENT_HOUR" -ge 8 ] && [ "$CURRENT_HOUR" -lt 17 ]; then
    echo "✅ Within operating hours (8 AM - 5 PM ET)"
else
    echo "❌ Outside operating hours (8 AM - 5 PM ET)"
fi
echo ""

# Check database
echo "🗄️ DATABASE"
echo "-----------"
if [ -f "analyst/database/signals.db" ]; then
    echo "✅ Database: analyst/database/signals.db"
    
    # Count recent signals
    RECENT_SIGNALS=$(sqlite3 analyst/database/signals.db "SELECT COUNT(*) FROM signals WHERE timestamp > datetime('now', '-1 hour');" 2>/dev/null || echo "0")
    echo "📊 Signals in last hour: $RECENT_SIGNALS"
else
    echo "❌ Database not found"
fi
echo ""

# Check API credentials
echo "🔑 API CREDENTIALS"
echo "-----------------"
if [ -f "analyst/scanner/.env" ]; then
    echo "✅ Alpaca API: Configured"
else
    echo "❌ Alpaca API: Not configured"
fi

if [ -f "analyst/notifications/config/token.json" ]; then
    echo "✅ Gmail API: Configured"
else
    echo "❌ Gmail API: Not configured"
fi

if [ -d "analyst/notifications/config" ] && [ "$(ls -A analyst/notifications/config 2>/dev/null)" ]; then
    echo "✅ Twitter API: Configured"
else
    echo "❌ Twitter API: Not configured"
fi
echo ""

echo "🎯 QUICK COMMANDS"
echo "----------------"
echo "Start Analyst:  ./analyst/start.sh"
echo "Start Investor: ./investor/start.sh"
echo "Stop Analyst:   ./analyst/stop.sh"
echo "Stop Investor:  ./investor/stop.sh"
echo "View Logs:      tail -f analyst/logs/analyst.log"
echo "View Logs:      tail -f investor/logs/investor.log"
