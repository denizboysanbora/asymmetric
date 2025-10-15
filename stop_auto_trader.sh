#!/bin/bash
# Stop the automated scanner and tweeter

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/auto_scan_tweet.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Auto-trader is not running (no PID file found)"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    echo "Stopping auto-trader (PID: $PID)..."
    kill "$PID"
    rm "$PID_FILE"
    echo "✅ Auto-trader stopped"
else
    echo "Process $PID is not running (removing stale PID file)"
    rm "$PID_FILE"
fi

