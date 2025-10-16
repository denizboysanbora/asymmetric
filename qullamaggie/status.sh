#!/bin/bash
# Check Qullamaggie Status

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/logs/qullamaggie.log"

echo "🔍 Qullamaggie Status Check"
echo "=========================="

# Check if process is running
PIDS=$(pgrep -f "qullamaggie.sh" || true)

if [ -z "$PIDS" ]; then
    echo "❌ Qullamaggie is NOT running"
else
    echo "✅ Qullamaggie is running (PID: $PIDS)"
fi

# Check lock file
LOCK_FILE="/tmp/qullamaggie.lock"
if [ -f "$LOCK_FILE" ]; then
    LOCK_PID=$(cat "$LOCK_FILE")
    echo "🔒 Lock file exists (PID: $LOCK_PID)"
    
    if ps -p "$LOCK_PID" > /dev/null 2>&1; then
        echo "   Lock is valid (process running)"
    else
        echo "   ⚠️  Lock is stale (process not running)"
    fi
else
    echo "🔓 No lock file"
fi

# Check log file
if [ -f "$LOG_FILE" ]; then
    echo "📝 Log file: $LOG_FILE"
    echo "   Size: $(ls -lh "$LOG_FILE" | awk '{print $5}')"
    echo "   Last modified: $(ls -l "$LOG_FILE" | awk '{print $6, $7, $8}')"
    
    echo ""
    echo "📋 Recent log entries (last 10 lines):"
    echo "--------------------------------------"
    tail -10 "$LOG_FILE" 2>/dev/null || echo "No log entries found"
else
    echo "📝 No log file found"
fi

# Check artifacts
ARTIFACTS_DIR="$SCRIPT_DIR/artifacts"
TODAY=$(TZ='America/New_York' date '+%Y-%m-%d')
TODAY_DIR="$ARTIFACTS_DIR/$TODAY"

echo ""
echo "📊 Today's Artifacts ($TODAY):"
echo "-------------------------------"

if [ -d "$TODAY_DIR" ]; then
    echo "✅ Artifacts directory exists: $TODAY_DIR"
    
    # List files
    for file in "$TODAY_DIR"/*; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            size=$(ls -lh "$file" | awk '{print $5}')
            modified=$(ls -l "$file" | awk '{print $6, $7, $8}')
            echo "   📄 $filename ($size, $modified)"
        fi
    done
else
    echo "❌ No artifacts for today"
fi

# Check virtual environment
VENV_PY="$SCRIPT_DIR/venv/bin/python3"
if [ -f "$VENV_PY" ]; then
    echo ""
    echo "🐍 Virtual environment: ✅ Found"
else
    echo ""
    echo "🐍 Virtual environment: ❌ Not found"
    echo "   Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
fi

echo ""
echo "=========================="