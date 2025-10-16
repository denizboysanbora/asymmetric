#!/bin/bash
# Analyst - Market Analysis & Signal Generation
# Schedule: 8 AM - 5 PM Eastern Time
# Scans stocks and crypto, generates signals, sends notifications

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
# Repo root (one level up from analyst/): .../asymmetric
ASYMMETRIC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Directories (relative to repo root)
SCANNER_DIR="$ASYMMETRIC_DIR/analyst/scanner"
NOTIFICATIONS_DIR="$ASYMMETRIC_DIR/analyst/notifications"
DATABASE_DIR="$ASYMMETRIC_DIR/analyst/database"

# Python executables
SCANNER_PY="$SCANNER_DIR/venv/bin/python3"
NOTIFICATIONS_PY="$NOTIFICATIONS_DIR/venv/bin/python3"

# Scripts
CRYPTO_SCRIPT="$SCANNER_DIR/compute_spike_params.py"
STOCKS_SCRIPT="$SCANNER_DIR/compute_spike_params_stocks.py"
EMAIL_SCRIPT="$NOTIFICATIONS_DIR/scripts/send_email.py"
TWEET_SCRIPT="$NOTIFICATIONS_DIR/scripts/tweet_with_limit.py"
LOG_SIGNAL_SCRIPT="$DATABASE_DIR/log_signal.py"
MARKET_STATUS_SCRIPT="$SCANNER_DIR/check_market_open.py"

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
# CRYPTO SIGNALS
# ========================================
echo "[$TIMESTAMP] 🔍 Scanning crypto markets..." | tee -a "$LOG_FILE"

CRYPTO_OUTPUT=$($SCANNER_PY $CRYPTO_SCRIPT 2>&1) || {
    echo "[$TIMESTAMP] ❌ Crypto scan failed: $CRYPTO_OUTPUT" | tee -a "$LOG_FILE"
    CRYPTO_OUTPUT=""
}

CRYPTO_SIGNALS=$(echo "$CRYPTO_OUTPUT" | grep -v "Scanning" | grep -v "Warning" | grep ' | Breakout$' || true)
CRYPTO_COUNT=$(echo "$CRYPTO_OUTPUT" | grep -v "Scanning" | grep -v "Warning" | wc -l)

if [ -n "$CRYPTO_SIGNALS" ]; then
    echo "[$TIMESTAMP] 🚨 Crypto breakout detected!" | tee -a "$LOG_FILE"
    echo "$CRYPTO_SIGNALS" | while IFS= read -r signal; do
        if $NOTIFICATIONS_PY $EMAIL_SCRIPT "$RECIPIENT" "Signal" "$signal" 2>/dev/null; then
            echo "[$TIMESTAMP] 📧 Crypto email sent: $signal" | tee -a "$LOG_FILE"
        else
            echo "[$TIMESTAMP] ❌ Crypto email failed: $signal" | tee -a "$LOG_FILE"
        fi
        
        # Tweet the signal
        if $NOTIFICATIONS_PY $TWEET_SCRIPT "$signal" 2>/dev/null; then
            echo "[$TIMESTAMP] 🐦 Crypto tweet sent: $signal" | tee -a "$LOG_FILE"
        else
            echo "[$TIMESTAMP] ❌ Crypto tweet failed: $signal" | tee -a "$LOG_FILE"
        fi
        
        # Log to database
        $SCANNER_PY $LOG_SIGNAL_SCRIPT "$signal" "crypto" 2>/dev/null || true
    done
else
    echo "[$TIMESTAMP] Crypto: No breakouts (scanned $CRYPTO_COUNT assets)" | tee -a "$LOG_FILE"
fi

# ========================================
# STOCK SIGNALS
# ========================================
echo "[$TIMESTAMP] 🔍 Scanning stock markets..." | tee -a "$LOG_FILE"

STOCKS_OUTPUT=$($SCANNER_PY $STOCKS_SCRIPT 2>&1) || {
    echo "[$TIMESTAMP] ❌ Stock scan failed: $STOCKS_OUTPUT" | tee -a "$LOG_FILE"
    STOCKS_OUTPUT=""
}

STOCKS_SIGNALS=$(echo "$STOCKS_OUTPUT" | grep -v "Scanning" | grep -v "Warning" | grep ' | Breakout$' || true)
STOCKS_COUNT=$(echo "$STOCKS_OUTPUT" | grep -v "Scanning" | grep -v "Warning" | wc -l)

STOCK_EMAILS_ENABLED=0
MARKET_STATUS=""
if MARKET_STATUS=$($SCANNER_PY $MARKET_STATUS_SCRIPT 2>&1); then
    if [ "$MARKET_STATUS" = "open" ]; then
        STOCK_EMAILS_ENABLED=1
        echo "[$TIMESTAMP] 📈 Market is open - emails enabled" | tee -a "$LOG_FILE"
    elif [ "$MARKET_STATUS" = "closed" ]; then
        echo "[$TIMESTAMP] 📉 Market is closed - emails disabled" | tee -a "$LOG_FILE"
    else
        echo "[$TIMESTAMP] ⚠️ Unexpected market status '$MARKET_STATUS' - emails disabled" | tee -a "$LOG_FILE"
    fi
else
    echo "[$TIMESTAMP] ⚠️ Could not check market status - emails disabled" | tee -a "$LOG_FILE"
fi

if [ -n "$STOCKS_SIGNALS" ] && [ "$STOCK_EMAILS_ENABLED" -eq 1 ]; then
    echo "[$TIMESTAMP] 🚨 Stock breakout detected!" | tee -a "$LOG_FILE"
    echo "$STOCKS_SIGNALS" | while IFS= read -r signal; do
        if $NOTIFICATIONS_PY $EMAIL_SCRIPT "$RECIPIENT" "Signal" "$signal" 2>/dev/null; then
            echo "[$TIMESTAMP] 📧 Stock email sent: $signal" | tee -a "$LOG_FILE"
        else
            echo "[$TIMESTAMP] ❌ Stock email failed: $signal" | tee -a "$LOG_FILE"
        fi
        
        # Tweet the signal
        if $NOTIFICATIONS_PY $TWEET_SCRIPT "$signal" 2>/dev/null; then
            echo "[$TIMESTAMP] 🐦 Stock tweet sent: $signal" | tee -a "$LOG_FILE"
        else
            echo "[$TIMESTAMP] ❌ Stock tweet failed: $signal" | tee -a "$LOG_FILE"
        fi
        
        # Log to database
        $SCANNER_PY $LOG_SIGNAL_SCRIPT "$signal" "stock" 2>/dev/null || true
    done
else
    if [ "$STOCK_EMAILS_ENABLED" -eq 0 ]; then
        echo "[$TIMESTAMP] Stock: Market closed - no signals processed" | tee -a "$LOG_FILE"
    else
        echo "[$TIMESTAMP] Stock: No breakouts (scanned $STOCKS_COUNT assets)" | tee -a "$LOG_FILE"
    fi
fi

echo "[$TIMESTAMP] Analyst analysis complete" | tee -a "$LOG_FILE"
