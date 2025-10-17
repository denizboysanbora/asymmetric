#!/bin/bash
# Breakout Analyst - Unified Breakout Scanner
# Schedule: 10 AM - 4 PM Eastern Time, weekdays, every 30 minutes
# Scans for both flag and range breakout setups and sends email notifications

set -euo pipefail

# Process locking to prevent duplicate executions
LOCK_FILE="/tmp/breakout_analyst.lock"
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') Breakout analyst already running (PID: $PID), skipping..." >> /Users/deniz/Code/asymmetric/analysts/breakout/logs/breakout_analyst.log
        exit 0
    else
        rm -f "$LOCK_FILE"
    fi
fi
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Repo root (three levels up from analysts/breakout/): .../asymmetric
ASYMMETRIC_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Load environment variables
if [ -f "$ASYMMETRIC_DIR/analysts/config/api_keys.env" ]; then
    source "$ASYMMETRIC_DIR/analysts/config/api_keys.env"
fi

# Directories
OUTPUT_DIR="$ASYMMETRIC_DIR/analysts/output"
ALPACA_DIR="$ASYMMETRIC_DIR/analysts/input/alpaca"
GMAIL_DIR="$OUTPUT_DIR/gmail"

# Python executables
BREAKOUT_PY="$ALPACA_DIR/venv/bin/python3"
GMAIL_PY="$ALPACA_DIR/venv/bin/python3"

# Scripts
BREAKOUT_SCRIPT="$SCRIPT_DIR/breakout_scanner.py"
EMAIL_SCRIPT="$GMAIL_DIR/send_email.py"

# Recipient
RECIPIENT="deniz@bora.box"

# Log files
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/breakout_analyst.log"

# Timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] Breakout analyst starting unified breakout analysis..." | tee -a "$LOG_FILE"

# Check if we're within operating hours (10 AM - 4 PM Eastern, weekdays)
CURRENT_HOUR=$(TZ='America/New_York' date '+%H')
CURRENT_DOW=$(TZ='America/New_York' date '+%u')  # 1=Monday, 7=Sunday
if [ "$CURRENT_HOUR" -lt 10 ] || [ "$CURRENT_HOUR" -ge 16 ] || [ "$CURRENT_DOW" -gt 5 ]; then
    echo "[$TIMESTAMP] Outside operating hours (10 AM - 4 PM ET, weekdays). Current hour: $CURRENT_HOUR, day: $CURRENT_DOW" | tee -a "$LOG_FILE"
    exit 0
fi

# ========================================
# UNIFIED BREAKOUT SCANNER
# ========================================
echo "[$TIMESTAMP] 🎯 Running unified breakout scanner..." | tee -a "$LOG_FILE"

BREAKOUT_OUTPUT=$($BREAKOUT_PY $BREAKOUT_SCRIPT 2>&1) || {
    echo "[$TIMESTAMP] ❌ Breakout scan failed: $BREAKOUT_OUTPUT" | tee -a "$LOG_FILE"
    BREAKOUT_OUTPUT=""
}

BREAKOUT_SIGNALS=$(echo "$BREAKOUT_OUTPUT" | grep -v "Scanning" | grep -v "Found" | grep '^\$[A-Z0-9]' || true)
# Pick top breakout by score (highest first)
TOP_BREAKOUT=$(echo "$BREAKOUT_SIGNALS" | head -1)
BREAKOUT_COUNT=$(echo "$BREAKOUT_SIGNALS" | wc -l)

if [ -n "$BREAKOUT_SIGNALS" ]; then
    echo "[$TIMESTAMP] 🎯 Breakout setups detected!" | tee -a "$LOG_FILE"
    
    # Use the top breakout setup
    if [ -n "$TOP_BREAKOUT" ]; then
        echo "[$TIMESTAMP] Selected breakout: $TOP_BREAKOUT" | tee -a "$LOG_FILE"
        
        # Determine signal type for email subject
        if echo "$TOP_BREAKOUT" | grep -q "Flag Breakout"; then
            EMAIL_SUBJECT="Flag Breakout Signal"
        elif echo "$TOP_BREAKOUT" | grep -q "Range Breakout"; then
            EMAIL_SUBJECT="Range Breakout Signal"
        else
            EMAIL_SUBJECT="Breakout Signal"
        fi
        
        # Send email notification
        if $GMAIL_PY $EMAIL_SCRIPT "$RECIPIENT" "$EMAIL_SUBJECT" "$TOP_BREAKOUT" 2>/dev/null; then
            echo "[$TIMESTAMP] 📧 Email sent: $TOP_BREAKOUT" | tee -a "$LOG_FILE"
        else
            echo "[$TIMESTAMP] ❌ Email failed: $TOP_BREAKOUT" | tee -a "$LOG_FILE"
        fi
        
        # Output to console
        echo "$TOP_BREAKOUT"
    fi
else
    echo "[$TIMESTAMP] Breakout: No setups found" | tee -a "$LOG_FILE"
fi

echo "[$TIMESTAMP] Breakout analyst analysis complete - Breakout setups found: $BREAKOUT_COUNT" | tee -a "$LOG_FILE"