#!/bin/bash
# Investor - Automated Crypto & Stocks Volatility Monitor
# Runs every 5 minutes: Emails and tweets immediately when signals detected

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASYMMETRIC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Directories (relative to repo root so deployment paths don't matter)
ALPACA_DIR="$ASYMMETRIC_DIR/alpaca/alpaca-mcp-server"
GMAIL_DIR="$ASYMMETRIC_DIR/gmail"
X_DIR="$ASYMMETRIC_DIR/x"
DATABASE_DIR="$ASYMMETRIC_DIR/database"

# Python executables
ALPACA_PY="$ALPACA_DIR/venv/bin/python3"
GMAIL_PY="$GMAIL_DIR/venv/bin/python3"
X_PY="$X_DIR/venv/bin/python3"

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
CRYPTO_SIGNALS=$($ALPACA_PY $CRYPTO_SCRIPT 2>&1 \
    | grep -v "Scanning" \
    | grep -v "Warning" \
    | grep ' | Breakout$' || true)

if [ -n "$CRYPTO_SIGNALS" ]; then
    # Send each crypto signal as separate email and log to database
    echo "$CRYPTO_SIGNALS" | while IFS= read -r signal; do
        $GMAIL_PY $EMAIL_SCRIPT "$RECIPIENT" "Signal" "$signal"
        $ALPACA_PY $LOG_SIGNAL_SCRIPT "$signal" "crypto" 2>/dev/null
        echo "[$TIMESTAMP] 📧 Crypto: $signal" | tee -a "$LOG_FILE"
        $X_PY $HOURLY_SUMMARY_SCRIPT --asset crypto --add "$signal" >/dev/null 2>&1 || true
    done
else
    echo "[$TIMESTAMP] Crypto: No signals" | tee -a "$LOG_FILE"
fi

# ========================================
# STOCK SIGNALS
# ========================================
STOCKS_SIGNALS=$($ALPACA_PY $STOCKS_SCRIPT 2>&1 \
    | grep -v "Scanning" \
    | grep -v "Warning" \
    | grep ' | Breakout$' || true)

STOCK_EMAILS_ENABLED=0
MARKET_STATUS=""
if MARKET_STATUS=$($ALPACA_PY $MARKET_STATUS_SCRIPT 2>&1); then
    if [ "$MARKET_STATUS" = "open" ]; then
        STOCK_EMAILS_ENABLED=1
    elif [ "$MARKET_STATUS" != "closed" ]; then
        echo "[$TIMESTAMP] ⚠️ Stocks: Unexpected market status '$MARKET_STATUS'; skipping emails." | tee -a "$LOG_FILE"
    fi
else
    echo "[$TIMESTAMP] ⚠️ Stocks: Market status check failed: ${MARKET_STATUS:-unknown}" | tee -a "$LOG_FILE"
    MARKET_STATUS="error"
fi

if [ -n "$STOCKS_SIGNALS" ]; then
    # Send each stock signal as separate email and log to database
    echo "$STOCKS_SIGNALS" | while IFS= read -r signal; do
        $ALPACA_PY $LOG_SIGNAL_SCRIPT "$signal" "stock" 2>/dev/null
        if [ "$STOCK_EMAILS_ENABLED" -eq 1 ]; then
            $GMAIL_PY $EMAIL_SCRIPT "$RECIPIENT" "Signal" "$signal"
            echo "[$TIMESTAMP] 📧 Stocks: $signal" | tee -a "$LOG_FILE"
        else
            case "$MARKET_STATUS" in
                closed) skip_reason="market closed" ;;
                error) skip_reason="market status unknown" ;;
                *) skip_reason="emails disabled" ;;
            esac
            echo "[$TIMESTAMP] 🔕 Stocks (email skipped - $skip_reason): $signal" | tee -a "$LOG_FILE"
        fi
        $X_PY $HOURLY_SUMMARY_SCRIPT --asset stock --add "$signal" >/dev/null 2>&1 || true
    done
else
    echo "[$TIMESTAMP] Stocks: No signals" | tee -a "$LOG_FILE"
fi

$X_PY $HOURLY_SUMMARY_SCRIPT --flush >/dev/null 2>&1 || true

echo "[$TIMESTAMP] Investor monitor completed" | tee -a "$LOG_FILE"
