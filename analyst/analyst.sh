#!/bin/bash
# Analyst - Market Analysis & Signal Generation
# Schedule: 8 AM - 5 PM Eastern Time
# Runs both breakout and trend scanners

set -euo pipefail

# Process locking to prevent duplicate executions
LOCK_FILE="/tmp/analyst.lock"
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') Analyst already running (PID: $PID), skipping..." >> /Users/deniz/Code/asymmetric/analyst/logs/analyst.log
        exit 0
    else
        rm -f "$LOCK_FILE"
    fi
fi
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Repo root (two levels up from analyst/): .../asymmetric
ASYMMETRIC_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Directories
INPUT_DIR="$SCRIPT_DIR/input"
OUTPUT_DIR="$SCRIPT_DIR/output"
ALPACA_DIR="$INPUT_DIR/alpaca"
BREAKOUT_DIR="$INPUT_DIR/breakout"
TREND_DIR="$INPUT_DIR/trend"
GMAIL_DIR="$OUTPUT_DIR/gmail"
TWEET_DIR="$OUTPUT_DIR/tweet"
DATABASE_DIR="$OUTPUT_DIR/database"
CONFIG_DIR="$SCRIPT_DIR/config"

# Python executables
ALPACA_PY="$ALPACA_DIR/venv/bin/python3"
BREAKOUT_PY="$ALPACA_PY"
TREND_PY="$ALPACA_PY"
GMAIL_PY="$ALPACA_PY"
TWEET_PY="$ALPACA_PY"
DATABASE_PY="$ALPACA_PY"

# Scripts
BREAKOUT_SCRIPT="$BREAKOUT_DIR/breakout_scanner.py"
TREND_SCRIPT="$TREND_DIR/trend_scanner.py"
EMAIL_SCRIPT="$GMAIL_DIR/send_email.py"
TWEET_SCRIPT="$TWEET_DIR/tweet_with_limit.py"
LOG_SIGNAL_SCRIPT="$DATABASE_DIR/log_signal.py"
MARKET_STATUS_SCRIPT="$ALPACA_DIR/check_market_open.py"

# Recipient
RECIPIENT="deniz@bora.box"

# Log files
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/analyst.log"

# Timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] Analyst starting market analysis..." | tee -a "$LOG_FILE"

# Check if we're within operating hours (8 AM - 5 PM Eastern)
CURRENT_HOUR=$(TZ='America/New_York' date '+%H')
if [ "$CURRENT_HOUR" -lt 8 ] || [ "$CURRENT_HOUR" -ge 17 ]; then
    echo "[$TIMESTAMP] Outside operating hours (8 AM - 5 PM ET). Current hour: $CURRENT_HOUR" | tee -a "$LOG_FILE"
    exit 0
fi

# ========================================
# BREAKOUT SCANNER
# ========================================
echo "[$TIMESTAMP] 🔍 Running breakout scanner..." | tee -a "$LOG_FILE"

BREAKOUT_OUTPUT=$($BREAKOUT_PY $BREAKOUT_SCRIPT 2>&1) || {
    echo "[$TIMESTAMP] ❌ Breakout scan failed: $BREAKOUT_OUTPUT" | tee -a "$LOG_FILE"
    BREAKOUT_OUTPUT=""
}

BREAKOUT_SIGNALS=$(echo "$BREAKOUT_OUTPUT" | grep -v "Scanning" | grep -v "Found" | grep ' | Breakout$' || true)
BREAKOUT_COUNT=$(echo "$BREAKOUT_SIGNALS" | wc -l)

if [ -n "$BREAKOUT_SIGNALS" ]; then
    echo "[$TIMESTAMP] 🚨 Breakout signals detected!" | tee -a "$LOG_FILE"
    echo "$BREAKOUT_SIGNALS" | while IFS= read -r signal; do
        if [ -n "$signal" ]; then
            # Determine asset class
            if echo "$signal" | grep -q "BTC\|ETH\|SOL\|XRP\|DOGE\|ADA\|AVAX\|LTC\|DOT\|LINK\|UNI\|ATOM"; then
                asset_class="crypto"
            else
                asset_class="stock"
            fi
            
            # Send email
            if $GMAIL_PY $EMAIL_SCRIPT "$RECIPIENT" "Signal" "$signal" 2>/dev/null; then
                echo "[$TIMESTAMP] 📧 Breakout email sent: $signal" | tee -a "$LOG_FILE"
            else
                echo "[$TIMESTAMP] ❌ Breakout email failed: $signal" | tee -a "$LOG_FILE"
            fi
            
            # Send tweet
            if $TWEET_PY $TWEET_SCRIPT "$signal" 2>/dev/null; then
                echo "[$TIMESTAMP] 🐦 Breakout tweet sent: $signal" | tee -a "$LOG_FILE"
            else
                echo "[$TIMESTAMP] ❌ Breakout tweet failed: $signal" | tee -a "$LOG_FILE"
            fi
            
            # Log to database
            $DATABASE_PY $LOG_SIGNAL_SCRIPT "$signal" "$asset_class" "Breakout" 2>/dev/null || true
        fi
    done
else
    echo "[$TIMESTAMP] Breakout: No signals found" | tee -a "$LOG_FILE"
fi

# ========================================
# TREND SCANNER
# ========================================
echo "[$TIMESTAMP] 📈 Running trend scanner..." | tee -a "$LOG_FILE"

TREND_OUTPUT=$($TREND_PY $TREND_SCRIPT 2>&1) || {
    echo "[$TIMESTAMP] ❌ Trend scan failed: $TREND_OUTPUT" | tee -a "$LOG_FILE"
    TREND_OUTPUT=""
}

TREND_SIGNALS=$(echo "$TREND_OUTPUT" | grep -v "Scanning" | grep -v "Found" | grep '^$[A-Z]' || true)
TREND_COUNT=$(echo "$TREND_SIGNALS" | wc -l)

if [ -n "$TREND_SIGNALS" ]; then
    echo "[$TIMESTAMP] 📊 Trend signals detected!" | tee -a "$LOG_FILE"
    echo "$TREND_SIGNALS" | while IFS= read -r signal; do
        if [ -n "$signal" ]; then
            # Send email
            if $GMAIL_PY $EMAIL_SCRIPT "$RECIPIENT" "Trend" "$signal" 2>/dev/null; then
                echo "[$TIMESTAMP] 📧 Trend email sent: $signal" | tee -a "$LOG_FILE"
            else
                echo "[$TIMESTAMP] ❌ Trend email failed: $signal" | tee -a "$LOG_FILE"
            fi
            
            # Send tweet
            if $TWEET_PY $TWEET_SCRIPT "$signal" 2>/dev/null; then
                echo "[$TIMESTAMP] 🐦 Trend tweet sent: $signal" | tee -a "$LOG_FILE"
            else
                echo "[$TIMESTAMP] ❌ Trend tweet failed: $signal" | tee -a "$LOG_FILE"
            fi
            
            # Log to database
            $DATABASE_PY $LOG_SIGNAL_SCRIPT "$signal" "stock" "Trending" 2>/dev/null || true
        fi
    done
else
    echo "[$TIMESTAMP] Trend: No signals found" | tee -a "$LOG_FILE"
fi

echo "[$TIMESTAMP] Analyst analysis complete - Breakouts: $BREAKOUT_COUNT, Trends: $TREND_COUNT" | tee -a "$LOG_FILE"