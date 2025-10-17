#!/bin/bash
# Analyst - Market Analysis & Signal Generation
# Schedule: 10 AM - 4 PM Eastern Time, weekdays, every 30 minutes
# Sends one signal per cycle: breakout preferred, highest mover fallback

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

# Load environment variables
if [ -f "$SCRIPT_DIR/config/api_keys.env" ]; then
    source "$SCRIPT_DIR/config/api_keys.env"
fi

# Directories
INPUT_DIR="$SCRIPT_DIR/input"
OUTPUT_DIR="$SCRIPT_DIR/output"
ALPACA_DIR="$INPUT_DIR/alpaca"
BREAKOUT_DIR="$INPUT_DIR/breakout"
TREND_DIR="$INPUT_DIR/trend"
QULLAMAGGIE_DIR="$INPUT_DIR/qullamaggie"
GMAIL_DIR="$OUTPUT_DIR/gmail"
TWEET_DIR="$OUTPUT_DIR/tweet"
DATABASE_DIR="$OUTPUT_DIR/database"
CONFIG_DIR="$SCRIPT_DIR/config"

# Python executables
ALPACA_PY="$ALPACA_DIR/venv/bin/python3"
BREAKOUT_PY="$ALPACA_PY"
TREND_PY="$ALPACA_PY"
QULLAMAGGIE_PY="$ALPACA_PY"
GMAIL_PY="$ALPACA_PY"
TWEET_PY="$ALPACA_PY"
DATABASE_PY="$ALPACA_PY"

# Scripts
BREAKOUT_SCRIPT="$BREAKOUT_DIR/breakout_scanner.py"
TREND_SCRIPT="$TREND_DIR/trend_scanner.py"
QULLAMAGGIE_SCRIPT="$QULLAMAGGIE_DIR/qullamaggie_scanner.py"
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

# Check if we're within operating hours (10 AM - 4 PM Eastern, weekdays)
CURRENT_HOUR=$(TZ='America/New_York' date '+%H')
CURRENT_DOW=$(TZ='America/New_York' date '+%u')  # 1=Monday, 7=Sunday
if [ "$CURRENT_HOUR" -lt 10 ] || [ "$CURRENT_HOUR" -ge 16 ] || [ "$CURRENT_DOW" -gt 5 ]; then
    echo "[$TIMESTAMP] Outside operating hours (10 AM - 4 PM ET, weekdays). Current hour: $CURRENT_HOUR, day: $CURRENT_DOW" | tee -a "$LOG_FILE"
    exit 0
fi

# ========================================
# MOMENTUM SCANNER
# ========================================
echo "[$TIMESTAMP] 🔍 Running momentum scanner..." | tee -a "$LOG_FILE"

MOMENTUM_OUTPUT=$($BREAKOUT_PY $BREAKOUT_SCRIPT 2>&1) || {
    echo "[$TIMESTAMP] ❌ Momentum scan failed: $MOMENTUM_OUTPUT" | tee -a "$LOG_FILE"
    MOMENTUM_OUTPUT=""
}

MOMENTUM_SIGNALS=$(echo "$MOMENTUM_OUTPUT" | grep -v "Scanning" | grep -v "Found" | grep ' | Momentum$' || true)
# Pick top momentum by absolute % move
TOP_MOMENTUM=$(echo "$MOMENTUM_SIGNALS" | awk '{match($0, /([+-][0-9]+(\.[0-9]+)?)%/); v=substr($0, RSTART, RLENGTH-1); gsub(/\+/,"",v); if (v<0) v=-v; printf "%012.6f\t%s\n", v, $0}' | sort -r | head -1 | cut -f2-)
MOMENTUM_COUNT=$(echo "$MOMENTUM_SIGNALS" | wc -l)

# ========================================
# SIGNAL SELECTION & NOTIFICATION LOGIC
# ========================================
SIGNAL_TO_SEND=""
SIGNAL_TYPE=""
SIGNAL_ASSET_CLASS=""

if [ -n "$MOMENTUM_SIGNALS" ]; then
    echo "[$TIMESTAMP] 🚨 Momentum signals detected!" | tee -a "$LOG_FILE"
    
    # Use the top momentum signal
    SIGNAL_TO_SEND="$TOP_MOMENTUM"
    SIGNAL_TYPE="Momentum"
    
    # All signals are now stock-only
    SIGNAL_ASSET_CLASS="stock"
    
    echo "[$TIMESTAMP] Selected momentum signal: $SIGNAL_TO_SEND" | tee -a "$LOG_FILE"
else
    echo "[$TIMESTAMP] Momentum: No signals found" | tee -a "$LOG_FILE"
fi

# ========================================
# TREND SCANNER
# ========================================
echo "[$TIMESTAMP] 📈 Running trend scanner..." | tee -a "$LOG_FILE"

TREND_OUTPUT=$($TREND_PY $TREND_SCRIPT 2>&1) || {
    echo "[$TIMESTAMP] ❌ Trend scan failed: $TREND_OUTPUT" | tee -a "$LOG_FILE"
    TREND_OUTPUT=""
}

TREND_SIGNALS=$(echo "$TREND_OUTPUT" | grep -v "Scanning" | grep -v "Found" | grep '^\$[A-Z0-9]' || true)
# Pick top trend by absolute % move
TOP_TREND=$(echo "$TREND_SIGNALS" | awk '{match($0, /([+-][0-9]+(\.[0-9]+)?)%/); v=substr($0, RSTART, RLENGTH-1); gsub(/\+/,"",v); if (v<0) v=-v; printf "%012.6f\t%s\n", v, $0}' | sort -r | head -1 | cut -f2-)
TREND_COUNT=$(echo "$TREND_SIGNALS" | wc -l)

if [ -n "$TREND_SIGNALS" ]; then
    echo "[$TIMESTAMP] 📊 Trend signals detected!" | tee -a "$LOG_FILE"
    
    # If no momentum was found, use the top trend as fallback
    if [ -z "$SIGNAL_TO_SEND" ]; then
        SIGNAL_TO_SEND="$TOP_TREND"
        SIGNAL_TYPE="Trending"
        SIGNAL_ASSET_CLASS="stock"  # Stock-only system
        echo "[$TIMESTAMP] Selected trend signal (fallback): $SIGNAL_TO_SEND" | tee -a "$LOG_FILE"
    fi
    
    # Log all trend signals to database (for tracking purposes)
    echo "$TREND_SIGNALS" | while IFS= read -r signal; do
        if [ -n "$signal" ]; then
            $DATABASE_PY $LOG_SIGNAL_SCRIPT "$signal" "stock" "Trending" 2>/dev/null || true
        fi
    done
else
    echo "[$TIMESTAMP] Trend: No signals found" | tee -a "$LOG_FILE"
fi

# ========================================
# QULLAMAGGIE SETUP SCANNER
# ========================================
echo "[$TIMESTAMP] 🎯 Running Qullamaggie setup scanner..." | tee -a "$LOG_FILE"

QULLAMAGGIE_OUTPUT=$($QULLAMAGGIE_PY $QULLAMAGGIE_SCRIPT 2>&1) || {
    echo "[$TIMESTAMP] ❌ Qullamaggie scan failed: $QULLAMAGGIE_OUTPUT" | tee -a "$LOG_FILE"
    QULLAMAGGIE_OUTPUT=""
}

QULLAMAGGIE_SIGNALS=$(echo "$QULLAMAGGIE_OUTPUT" | grep -v "Scanning" | grep -v "Found" | grep '^\$[A-Z0-9]' || true)
# Pick top Qullamaggie setup by score (highest first)
TOP_QULLAMAGGIE=$(echo "$QULLAMAGGIE_SIGNALS" | head -1)
QULLAMAGGIE_COUNT=$(echo "$QULLAMAGGIE_SIGNALS" | wc -l)

if [ -n "$QULLAMAGGIE_SIGNALS" ]; then
    echo "[$TIMESTAMP] 🎯 Qullamaggie setups detected!" | tee -a "$LOG_FILE"
    
    # If no momentum or trend was found, use the top Qullamaggie setup as fallback
    if [ -z "$SIGNAL_TO_SEND" ]; then
        SIGNAL_TO_SEND="$TOP_QULLAMAGGIE"
        SIGNAL_TYPE="Qullamaggie"
        SIGNAL_ASSET_CLASS="stock"  # Stock-only system
        echo "[$TIMESTAMP] Selected Qullamaggie setup (fallback): $SIGNAL_TO_SEND" | tee -a "$LOG_FILE"
    fi
    
    # Log all Qullamaggie signals to database (for tracking purposes)
    echo "$QULLAMAGGIE_SIGNALS" | while IFS= read -r signal; do
        if [ -n "$signal" ]; then
            $DATABASE_PY $LOG_SIGNAL_SCRIPT "$signal" "stock" "Qullamaggie" 2>/dev/null || true
        fi
    done
else
    echo "[$TIMESTAMP] Qullamaggie: No setups found" | tee -a "$LOG_FILE"
fi

# ========================================
# SEND NOTIFICATIONS (ONE SIGNAL ONLY)
# ========================================
if [ -n "$SIGNAL_TO_SEND" ]; then
    echo "[$TIMESTAMP] 📤 Sending notifications for selected signal..." | tee -a "$LOG_FILE"
    
    # Send email with appropriate subject based on signal type
    EMAIL_SUBJECT="Momentum"
    if [[ "$SIGNAL_TYPE" == "Trending" ]]; then
        EMAIL_SUBJECT="Trend"
    elif [[ "$SIGNAL_TYPE" == "Qullamaggie" ]]; then
        EMAIL_SUBJECT="Qullamaggie"
    fi
    
    if $GMAIL_PY $EMAIL_SCRIPT "$RECIPIENT" "$EMAIL_SUBJECT" "$SIGNAL_TO_SEND" 2>/dev/null; then
        echo "[$TIMESTAMP] 📧 Email sent: $SIGNAL_TO_SEND" | tee -a "$LOG_FILE"
    else
        echo "[$TIMESTAMP] ❌ Email failed: $SIGNAL_TO_SEND" | tee -a "$LOG_FILE"
    fi
    
    # Send tweet
    if tweet_output=$($TWEET_PY "$TWEET_SCRIPT" "$SIGNAL_TO_SEND" 2>&1); then
        echo "[$TIMESTAMP] 🐦 Tweet sent: $SIGNAL_TO_SEND" | tee -a "$LOG_FILE"
        if [ -n "$tweet_output" ]; then
            while IFS= read -r line; do
                echo "[$TIMESTAMP]    ↳ $line" | tee -a "$LOG_FILE"
            done <<< "$tweet_output"
        fi
    else
        echo "[$TIMESTAMP] ❌ Tweet failed: $SIGNAL_TO_SEND" | tee -a "$LOG_FILE"
        if [ -n "$tweet_output" ]; then
            while IFS= read -r line; do
                echo "[$TIMESTAMP]    ↳ $line" | tee -a "$LOG_FILE"
            done <<< "$tweet_output"
        fi
    fi
    
    # Log the selected signal to database
    $DATABASE_PY $LOG_SIGNAL_SCRIPT "$SIGNAL_TO_SEND" "$SIGNAL_ASSET_CLASS" "$SIGNAL_TYPE" 2>/dev/null || true
else
    echo "[$TIMESTAMP] No signal selected - no notifications sent" | tee -a "$LOG_FILE"
fi

echo "[$TIMESTAMP] Analyst analysis complete - Momentum: $MOMENTUM_COUNT, Trends: $TREND_COUNT, Qullamaggie: $QULLAMAGGIE_COUNT, Signal Sent: $SIGNAL_TYPE" | tee -a "$LOG_FILE"
