#!/bin/bash
# Stop Analyst Mode

set -euo pipefail

echo "🛑 Stopping Analyst Mode..."

# Find and kill analyst processes
ANALYST_PIDS=$(pgrep -f "analyst.sh" || true)

if [ -z "$ANALYST_PIDS" ]; then
    echo "⚠️  Analyst is not running"
    exit 0
fi

echo "Found Analyst processes: $ANALYST_PIDS"

# Kill the processes
for pid in $ANALYST_PIDS; do
    echo "Killing process $pid..."
    kill "$pid" 2>/dev/null || true
done

# Wait a moment for graceful shutdown
sleep 2

# Force kill if still running
REMAINING_PIDS=$(pgrep -f "analyst.sh" || true)
if [ -n "$REMAINING_PIDS" ]; then
    echo "Force killing remaining processes: $REMAINING_PIDS"
    for pid in $REMAINING_PIDS; do
        kill -9 "$pid" 2>/dev/null || true
    done
fi

echo "✅ Analyst stopped"
