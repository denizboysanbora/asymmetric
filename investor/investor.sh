#!/bin/bash
# Investor - Trading Execution & Portfolio Management
# Executes trades based on analyst signals using Alpaca API

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
# Repo root (one level up from investor/): .../asymmetric
ASYMMETRIC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Directories
TRADING_DIR="$ASYMMETRIC_DIR/investor/trading"
PORTFOLIO_DIR="$ASYMMETRIC_DIR/investor/portfolio"
EXECUTION_DIR="$ASYMMETRIC_DIR/investor/execution"
DATABASE_DIR="$ASYMMETRIC_DIR/analyst/database"

# Python executables (reuse analyst scanner venv for now)
SCANNER_PY="$ASYMMETRIC_DIR/analyst/scanner/venv/bin/python3"

# Scripts
EXECUTOR_SCRIPT="$TRADING_DIR/executor.py"
LOG_SIGNAL_SCRIPT="$DATABASE_DIR/log_signal.py"

# Log files
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/investor.log"

# Timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] Investor starting trading execution..." | tee -a "$LOG_FILE"

# Check if we're within trading hours (8 AM - 5 PM Eastern)
CURRENT_HOUR=$(TZ='America/New_York' date '+%H')
if [ "$CURRENT_HOUR" -lt 8 ] || [ "$CURRENT_HOUR" -ge 17 ]; then
    echo "[$TIMESTAMP] Outside trading hours (8 AM - 5 PM ET). Current hour: $CURRENT_HOUR" | tee -a "$LOG_FILE"
    exit 0
fi

# ========================================
# PORTFOLIO MANAGEMENT
# ========================================
echo "[$TIMESTAMP] 📊 Checking portfolio status..." | tee -a "$LOG_FILE"

# Get current positions
if [ -f "$EXECUTOR_SCRIPT" ]; then
    PORTFOLIO_OUTPUT=$($SCANNER_PY $EXECUTOR_SCRIPT --portfolio 2>&1) || {
        echo "[$TIMESTAMP] ❌ Portfolio check failed: $PORTFOLIO_OUTPUT" | tee -a "$LOG_FILE"
        PORTFOLIO_OUTPUT=""
    }
    echo "[$TIMESTAMP] Portfolio status: $PORTFOLIO_OUTPUT" | tee -a "$LOG_FILE"
else
    echo "[$TIMESTAMP] ⚠️ Portfolio executor not found" | tee -a "$LOG_FILE"
fi

# ========================================
# SIGNAL PROCESSING & TRADING
# ========================================
echo "[$TIMESTAMP] 🔄 Processing signals for trading..." | tee -a "$LOG_FILE"

# Check for recent signals in database
if [ -f "$LOG_SIGNAL_SCRIPT" ]; then
    # Get recent signals (last 5 minutes)
    RECENT_SIGNALS=$($SCANNER_PY -c "
import sqlite3
import os
from datetime import datetime, timedelta

db_path = '$DATABASE_DIR/signals.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get signals from last 5 minutes
    cutoff = datetime.now() - timedelta(minutes=5)
    cursor.execute('''
        SELECT symbol, price, change_pct, tr_atr, z_score, signal_type, asset_class 
        FROM signals 
        WHERE timestamp > ? AND signal_type = 'Breakout'
        ORDER BY timestamp DESC
    ''', (cutoff.strftime('%Y-%m-%d %H:%M:%S'),))
    
    signals = cursor.fetchall()
    for signal in signals:
        print(f'{signal[0]}|{signal[1]}|{signal[2]}|{signal[3]}|{signal[4]}|{signal[5]}|{signal[6]}')
    conn.close()
" 2>/dev/null || true)
    
    if [ -n "$RECENT_SIGNALS" ]; then
        echo "[$TIMESTAMP] 🚨 Found recent signals for trading:" | tee -a "$LOG_FILE"
        echo "$RECENT_SIGNALS" | while IFS= read -r signal_line; do
            if [ -n "$signal_line" ]; then
                IFS='|' read -r symbol price change_pct tr_atr z_score signal_type asset_class <<< "$signal_line"
                echo "[$TIMESTAMP] Processing signal: $symbol at $price (${change_pct}%)" | tee -a "$LOG_FILE"
                
                # Execute trade based on signal
                if [ -f "$EXECUTOR_SCRIPT" ]; then
                    TRADE_OUTPUT=$($SCANNER_PY $EXECUTOR_SCRIPT --trade "$symbol" "$price" "$change_pct" "$asset_class" 2>&1) || {
                        echo "[$TIMESTAMP] ❌ Trade execution failed for $symbol: $TRADE_OUTPUT" | tee -a "$LOG_FILE"
                    }
                    echo "[$TIMESTAMP] Trade result for $symbol: $TRADE_OUTPUT" | tee -a "$LOG_FILE"
                else
                    echo "[$TIMESTAMP] ⚠️ Trade executor not found for $symbol" | tee -a "$LOG_FILE"
                fi
            fi
        done
    else
        echo "[$TIMESTAMP] No recent signals found for trading" | tee -a "$LOG_FILE"
    fi
else
    echo "[$TIMESTAMP] ⚠️ Signal database not found" | tee -a "$LOG_FILE"
fi

# ========================================
# RISK MANAGEMENT
# ========================================
echo "[$TIMESTAMP] 🛡️ Running risk management checks..." | tee -a "$LOG_FILE"

# Check position sizes, stop losses, etc.
if [ -f "$EXECUTOR_SCRIPT" ]; then
    RISK_OUTPUT=$($SCANNER_PY $EXECUTOR_SCRIPT --risk-check 2>&1) || {
        echo "[$TIMESTAMP] ❌ Risk check failed: $RISK_OUTPUT" | tee -a "$LOG_FILE"
        RISK_OUTPUT=""
    }
    echo "[$TIMESTAMP] Risk management: $RISK_OUTPUT" | tee -a "$LOG_FILE"
else
    echo "[$TIMESTAMP] ⚠️ Risk management executor not found" | tee -a "$LOG_FILE"
fi

echo "[$TIMESTAMP] Investor trading execution complete" | tee -a "$LOG_FILE"