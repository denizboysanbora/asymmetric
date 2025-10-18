#!/bin/bash
# Check status of Investor mode

set -euo pipefail

echo "💰 Paper Trading Investor Status"
echo "================================="
echo ""

# Check Investor Mode
echo "💰 INVESTOR MODE (Paper Trading Execution)"
echo "------------------------------------------"
INVESTOR_PIDS=$(pgrep -f "investor.sh" 2>/dev/null || true)
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
if [ "$CURRENT_HOUR" -ge 10 ] && [ "$CURRENT_HOUR" -lt 16 ]; then
    echo "✅ Within operating hours (10 AM - 4 PM ET)"
else
    echo "❌ Outside operating hours (10 AM - 4 PM ET)"
fi
echo ""

# Check API credentials
echo "🔑 API CREDENTIALS"
echo "-----------------"
if [ -f "analyst/input/alpaca/.env" ]; then
    echo "✅ Alpaca API: Configured"
else
    echo "❌ Alpaca API: Not configured"
fi
echo ""

# Check portfolio state
echo "💼 PORTFOLIO STATE"
echo "-----------------"
if [ -f "investor/portfolio_state.json" ]; then
    echo "✅ Portfolio state file exists"
    # Show portfolio summary if possible
    if command -v python3 >/dev/null 2>&1; then
        echo "📊 Portfolio summary:"
        python3 -c "
import json
try:
    with open('investor/portfolio_state.json', 'r') as f:
        data = json.load(f)
    print(f'   Total Value: \${data.get(\"total_value\", 0):,.2f}')
    print(f'   Cash: \${data.get(\"cash\", 0):,.2f}')
    print(f'   Positions: {len(data.get(\"positions\", {}))}')
except:
    print('   Could not read portfolio state')
" 2>/dev/null || echo "   Could not read portfolio state"
    else
        echo "   Portfolio state file found"
    fi
else
    echo "❌ No portfolio state file (new investor)"
fi
echo ""

echo "🎯 QUICK COMMANDS"
echo "----------------"
echo "Start Investor:  ./investor/start.sh"
echo "Stop Investor:   ./investor/stop.sh"
echo "View Logs:       tail -f investor/logs/investor.log"
