#!/bin/bash
# Investor - Paper Trading Execution
# Monitors breakout signals and executes paper trades

set -euo pipefail

# Process locking to prevent duplicate executions
LOCK_FILE="/tmp/investor.lock"
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') Investor already running (PID: $PID), skipping..." >> /Users/deniz/Code/asymmetric/investor/logs/investor.log
        exit 0
    else
        rm -f "$LOCK_FILE"
    fi
fi
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASYMMETRIC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load environment variables
if [ -f "$ASYMMETRIC_DIR/analyst/config/api_keys.env" ]; then
    source "$ASYMMETRIC_DIR/analyst/config/api_keys.env"
fi

# Directories
ALPACA_DIR="$ASYMMETRIC_DIR/analyst/input/alpaca"
INVESTOR_DIR="$SCRIPT_DIR"

# Python executables
INVESTOR_PY="$ALPACA_DIR/venv/bin/python3"

# Scripts
PAPER_TRADER_SCRIPT="$INVESTOR_DIR/paper_trader.py"

# Log files
LOG_DIR="$INVESTOR_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/investor.log"

# Timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] Investor starting paper trading execution..." | tee -a "$LOG_FILE"

# Check if we're within operating hours (10 AM - 4 PM Eastern, weekdays)
CURRENT_HOUR=$(TZ='America/New_York' date '+%H')
CURRENT_DOW=$(TZ='America/New_York' date '+%u')  # 1=Monday, 7=Sunday
if [ "$CURRENT_HOUR" -lt 10 ] || [ "$CURRENT_HOUR" -ge 16 ] || [ "$CURRENT_DOW" -gt 5 ]; then
    echo "[$TIMESTAMP] Outside operating hours (10 AM - 4 PM ET, weekdays). Current hour: $CURRENT_HOUR, day: $CURRENT_DOW" | tee -a "$LOG_FILE"
    exit 0
fi

# ========================================
# PAPER TRADING EXECUTION
# ========================================
echo "[$TIMESTAMP] 💰 Running paper trading execution..." | tee -a "$LOG_FILE"

# Check for recent breakout signals from analyst logs
ANALYSTS_LOG="$ASYMMETRIC_DIR/analyst/breakout/logs/breakout_analyst.log"
if [ -f "$ANALYSTS_LOG" ]; then
    # Get the most recent breakout signal from analyst logs
    RECENT_SIGNAL=$(tail -50 "$ANALYSTS_LOG" | grep -E '\$[A-Z0-9]+.*Breakout' | tail -1)
    
    if [ -n "$RECENT_SIGNAL" ]; then
        echo "[$TIMESTAMP] 📊 Found recent breakout signal: $RECENT_SIGNAL" | tee -a "$LOG_FILE"
        
        # Execute paper trade
        if $INVESTOR_PY $PAPER_TRADER_SCRIPT "$RECENT_SIGNAL" 2>&1 | tee -a "$LOG_FILE"; then
            echo "[$TIMESTAMP] ✅ Paper trading execution completed" | tee -a "$LOG_FILE"
        else
            echo "[$TIMESTAMP] ❌ Paper trading execution failed" | tee -a "$LOG_FILE"
        fi
    else
        echo "[$TIMESTAMP] No recent breakout signals found" | tee -a "$LOG_FILE"
    fi
else
    echo "[$TIMESTAMP] Analyst log file not found: $ANALYSTS_LOG" | tee -a "$LOG_FILE"
fi

echo "[$TIMESTAMP] Investor execution complete" | tee -a "$LOG_FILE"
