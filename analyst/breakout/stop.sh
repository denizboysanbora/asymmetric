#!/bin/bash
# Stop Breakout Analyst

set -euo pipefail

echo "🛑 Stopping Breakout Analyst..."

# Find and kill breakout analyst processes
BREAKOUT_ANALYST_PIDS=$(pgrep -f "breakout_analyst.sh" || true)

if [ -z "$BREAKOUT_ANALYST_PIDS" ]; then
    echo "⚠️  Breakout analyst is not running"
    exit 0
fi

echo "Found Breakout analyst processes: $BREAKOUT_ANALYST_PIDS"

# Kill the processes
for pid in $BREAKOUT_ANALYST_PIDS; do
    echo "Killing process $pid..."
    kill "$pid" 2>/dev/null || true
done

# Wait a moment for graceful shutdown
sleep 2

# Force kill if still running
REMAINING_PIDS=$(pgrep -f "breakout_analyst.sh" || true)
if [ -n "$REMAINING_PIDS" ]; then
    echo "Force killing remaining processes: $REMAINING_PIDS"
    for pid in $REMAINING_PIDS; do
        kill -9 "$pid" 2>/dev/null || true
    done
fi

echo "✅ Breakout analyst stopped"