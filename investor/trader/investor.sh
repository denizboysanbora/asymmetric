#!/bin/bash
# Investor - Automated Crypto & Stocks Volatility Monitor
# Runs every 5 minutes: Emails and tweets immediately when signals detected

set -euo pipefail

# Process locking to prevent duplicate executions
LOCK_FILE="/tmp/investor.lock"
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') Investor already running (PID: $PID), skipping..." >> /Users/deniz/Code/asymmetric/investor/trader/logs/investor.log
        exit 0
    else
        rm -f "$LOCK_FILE"
    fi
fi
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Repo root (two levels up from trader/): .../asymmetric
ASYMMETRIC_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Directories (relative to repo root so deployment paths don't matter)
ALPACA_DIR="$ASYMMETRIC_DIR/analyst/alpaca/alpaca-mcp-server"
GMAIL_DIR="$ASYMMETRIC_DIR/output/gmail"
X_DIR="$ASYMMETRIC_DIR/output/x"
DATABASE_DIR="$ASYMMETRIC_DIR/analyst/database"

# Python executables
ALPACA_PY="$ALPACA_DIR/venv/bin/python3"
GMAIL_PY="$GMAIL_DIR/venv/bin/python3"
# X does not have its own venv; reuse Alpaca venv which has deps installed
X_PY="$ALPACA_PY"

# Scripts
CRYPTO_SCRIPT="$ALPACA_DIR/compute_spike_params.py"
STOCKS_SCRIPT="$ALPACA_DIR/compute_spike_params_stocks.py"
EMAIL_SCRIPT="$GMAIL_DIR/scripts/send_email.py"
HOURLY_SUMMARY_SCRIPT="$X_DIR/scripts/tweet_hourly_summary.py"
LOG_SIGNAL_SCRIPT="$DATABASE_DIR/log_signal.py"
MARKET_STATUS_SCRIPT="$ALPACA_DIR/check_market_open.py"

# Recipient
RECIPIENT="deniz@bora.box"

# Log files
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/investor.log"

# Timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] Investor monitor starting..." | tee -a "$LOG_FILE"

# ========================================
# CRYPTO SIGNALS
# ========================================
echo "[$TIMESTAMP] 🔍 Scanning crypto markets..." | tee -a "$LOG_FILE"

CRYPTO_OUTPUT=$($ALPACA_PY $CRYPTO_SCRIPT 2>&1) || {
    echo "[$TIMESTAMP] ❌ Crypto scan failed: $CRYPTO_OUTPUT" | tee -a "$LOG_FILE"
    CRYPTO_OUTPUT=""
}

CRYPTO_SIGNALS=$(echo "$CRYPTO_OUTPUT" | grep -v "Scanning" | grep -v "Warning" | grep ' | Breakout$' || true)
CRYPTO_COUNT=$(echo "$CRYPTO_OUTPUT" | grep -v "Scanning" | grep -v "Warning" | wc -l)

if [ -n "$CRYPTO_SIGNALS" ]; then
    echo "[$TIMESTAMP] 🚨 Crypto breakout detected!" | tee -a "$LOG_FILE"
    echo "$CRYPTO_SIGNALS" | while IFS= read -r signal; do
        if $GMAIL_PY $EMAIL_SCRIPT "$RECIPIENT" "Signal" "$signal" 2>/dev/null; then
            echo "[$TIMESTAMP] 📧 Crypto email sent: $signal" | tee -a "$LOG_FILE"
        else
            echo "[$TIMESTAMP] ❌ Crypto email failed: $signal" | tee -a "$LOG_FILE"
        fi
        $ALPACA_PY $LOG_SIGNAL_SCRIPT "$signal" "crypto" 2>/dev/null || true
        $X_PY $HOURLY_SUMMARY_SCRIPT --asset crypto --add "$signal" >/dev/null 2>&1 || true
    done
else
    echo "[$TIMESTAMP] Crypto: No breakouts (scanned $CRYPTO_COUNT assets)" | tee -a "$LOG_FILE"
fi

# ========================================
# STOCK SIGNALS
# ========================================
echo "[$TIMESTAMP] 🔍 Scanning stock markets..." | tee -a "$LOG_FILE"

STOCKS_OUTPUT=$($ALPACA_PY $STOCKS_SCRIPT 2>&1) || {
    echo "[$TIMESTAMP] ❌ Stock scan failed: $STOCKS_OUTPUT" | tee -a "$LOG_FILE"
    STOCKS_OUTPUT=""
}

STOCKS_SIGNALS=$(echo "$STOCKS_OUTPUT" | grep -v "Scanning" | grep -v "Warning" | grep ' | Breakout$' || true)
STOCKS_COUNT=$(echo "$STOCKS_OUTPUT" | grep -v "Scanning" | grep -v "Warning" | wc -l)

STOCK_EMAILS_ENABLED=0
MARKET_STATUS=""
if MARKET_STATUS=$($ALPACA_PY $MARKET_STATUS_SCRIPT 2>&1); then
    if [ "$MARKET_STATUS" = "open" ]; then
        STOCK_EMAILS_ENABLED=1
        echo "[$TIMESTAMP] 📈 Market is open - emails enabled" | tee -a "$LOG_FILE"
    elif [ "$MARKET_STATUS" = "closed" ]; then
        echo "[$TIMESTAMP] 📉 Market is closed - emails disabled" | tee -a "$LOG_FILE"
    else
        echo "[$TIMESTAMP] ⚠️ Unexpected market status '$MARKET_STATUS' - emails disabled" | tee -a "$LOG_FILE"
    fi
else
    echo "[$TIMESTAMP] ⚠️ Market status check failed: ${MARKET_STATUS:-unknown} - emails disabled" | tee -a "$LOG_FILE"
    MARKET_STATUS="error"
fi

if [ -n "$STOCKS_SIGNALS" ]; then
    echo "[$TIMESTAMP] 🚨 Stock breakout detected!" | tee -a "$LOG_FILE"
    echo "$STOCKS_SIGNALS" | while IFS= read -r signal; do
        $ALPACA_PY $LOG_SIGNAL_SCRIPT "$signal" "stock" 2>/dev/null || true
        if [ "$STOCK_EMAILS_ENABLED" -eq 1 ]; then
            if $GMAIL_PY $EMAIL_SCRIPT "$RECIPIENT" "Signal" "$signal" 2>/dev/null; then
                echo "[$TIMESTAMP] 📧 Stock email sent: $signal" | tee -a "$LOG_FILE"
            else
                echo "[$TIMESTAMP] ❌ Stock email failed: $signal" | tee -a "$LOG_FILE"
            fi
        else
            case "$MARKET_STATUS" in
                closed) skip_reason="market closed" ;;
                error) skip_reason="market status unknown" ;;
                *) skip_reason="emails disabled" ;;
            esac
            echo "[$TIMESTAMP] 🔕 Stock signal (email skipped - $skip_reason): $signal" | tee -a "$LOG_FILE"
        fi
        $X_PY $HOURLY_SUMMARY_SCRIPT --asset stock --add "$signal" >/dev/null 2>&1 || true
    done
else
    echo "[$TIMESTAMP] Stocks: No breakouts (scanned $STOCKS_COUNT assets, market: $MARKET_STATUS)" | tee -a "$LOG_FILE"
fi

$X_PY $HOURLY_SUMMARY_SCRIPT --flush >/dev/null 2>&1 || true

echo "[$TIMESTAMP] Investor monitor completed" | tee -a "$LOG_FILE"
