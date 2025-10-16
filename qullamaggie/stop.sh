#!/bin/bash
# Stop Qullamaggie Mode

set -euo pipefail

echo "🛑 Stopping Qullamaggie..."

# Find and kill qullamaggie processes
PIDS=$(pgrep -f "qullamaggie.sh" || true)

if [ -z "$PIDS" ]; then
    echo "ℹ️  Qullamaggie is not running"
    exit 0
fi

echo "Found Qullamaggie processes: $PIDS"

# Kill processes
for PID in $PIDS; do
    echo "Stopping process $PID..."
    kill -TERM "$PID" 2>/dev/null || true
    
    # Wait a bit for graceful shutdown
    sleep 2
    
    # Force kill if still running
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Force stopping process $PID..."
        kill -KILL "$PID" 2>/dev/null || true
    fi
done

# Clean up lock file
LOCK_FILE="/tmp/qullamaggie.lock"
if [ -f "$LOCK_FILE" ]; then
    rm -f "$LOCK_FILE"
    echo "Cleaned up lock file"
fi

echo "✅ Qullamaggie stopped"