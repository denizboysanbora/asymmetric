#!/bin/bash
# Stop Investor Mode

set -euo pipefail

echo "🛑 Stopping Investor Mode..."

# Find and kill investor processes
INVESTOR_PIDS=$(pgrep -f "investor.sh" || true)

if [ -z "$INVESTOR_PIDS" ]; then
    echo "⚠️  Investor is not running"
    exit 0
fi

echo "Found Investor processes: $INVESTOR_PIDS"

# Kill the processes
for pid in $INVESTOR_PIDS; do
    echo "Killing process $pid..."
    kill "$pid" 2>/dev/null || true
done

# Wait a moment for graceful shutdown
sleep 2

# Force kill if still running
REMAINING_PIDS=$(pgrep -f "investor.sh" || true)
if [ -n "$REMAINING_PIDS" ]; then
    echo "Force killing remaining processes: $REMAINING_PIDS"
    for pid in $REMAINING_PIDS; do
        kill -9 "$pid" 2>/dev/null || true
    done
fi

echo "✅ Investor stopped"
