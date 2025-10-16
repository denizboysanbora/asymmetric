#!/bin/bash
# Qullamaggie - Momentum Pattern Analyzer
# Schedule: 8 AM - 4 PM Eastern Time, weekdays
# Email notifications only (no tweets)

set -euo pipefail

# Process locking to prevent duplicate executions
LOCK_FILE="/tmp/qullamaggie.lock"
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') Qullamaggie already running (PID: $PID), skipping..." >> /Users/deniz/Code/asymmetric/qullamaggie/logs/qullamaggie.log
        exit 0
    else
        rm -f "$LOCK_FILE"
    fi
fi
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment variables
if [ -f "$SCRIPT_DIR/config/api_keys.env" ]; then
    source "$SCRIPT_DIR/config/api_keys.env"
fi

# Directories
OUTPUT_DIR="$SCRIPT_DIR/output"
GMAIL_DIR="$OUTPUT_DIR/gmail"
CONFIG_DIR="$SCRIPT_DIR/config"
ARTIFACTS_DIR="$SCRIPT_DIR/artifacts"

# Python executable (will be set to venv when available)
QULLAMAGGIE_PY="$SCRIPT_DIR/venv/bin/python3"

# Scripts
EMAIL_SCRIPT="$GMAIL_DIR/send_email.py"

# Recipient
RECIPIENT="deniz@bora.box"

# Log files
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/qullamaggie.log"

# Timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] Qullamaggie starting momentum analysis..." | tee -a "$LOG_FILE"

# Check if we're within operating hours (8 AM - 4 PM Eastern, weekdays)
CURRENT_HOUR=$(TZ='America/New_York' date '+%H')
CURRENT_DOW=$(TZ='America/New_York' date '+%u')  # 1=Monday, 7=Sunday
if [ "$CURRENT_HOUR" -lt 8 ] || [ "$CURRENT_HOUR" -ge 16 ] || [ "$CURRENT_DOW" -gt 5 ]; then
    echo "[$TIMESTAMP] Outside operating hours (8 AM - 4 PM ET, weekdays). Current hour: $CURRENT_HOUR, day: $CURRENT_DOW" | tee -a "$LOG_FILE"
    exit 0
fi

# Check if virtual environment exists
if [ ! -f "$QULLAMAGGIE_PY" ]; then
    echo "[$TIMESTAMP] ❌ Virtual environment not found at $QULLAMAGGIE_PY" | tee -a "$LOG_FILE"
    echo "[$TIMESTAMP] Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt" | tee -a "$LOG_FILE"
    exit 1
fi

# Determine current time and market status
CURRENT_TIME=$(TZ='America/New_York' date '+%H:%M')
MARKET_OPEN_TIME="09:30"
MARKET_OR_TIME="09:35"

# ========================================
# PRE-MARKET ANALYSIS (< 9:30 AM)
# ========================================
if [[ "$CURRENT_TIME" < "$MARKET_OPEN_TIME" ]]; then
    echo "[$TIMESTAMP] 🌅 Running pre-market analysis..." | tee -a "$LOG_FILE"
    
    ANALYSIS_OUTPUT=$($QULLAMAGGIE_PY -m qullamaggie.run analyze 2>&1) || {
        echo "[$TIMESTAMP] ❌ Pre-market analysis failed: $ANALYSIS_OUTPUT" | tee -a "$LOG_FILE"
        exit 1
    }
    
    echo "[$TIMESTAMP] ✅ Pre-market analysis complete" | tee -a "$LOG_FILE"
    
    # Check if we have candidates to send email about
    TODAY_DIR="$ARTIFACTS_DIR/$(TZ='America/New_York' date '+%Y-%m-%d')"
    CANDIDATES_FILE="$TODAY_DIR/candidates.json"
    
    if [ -f "$CANDIDATES_FILE" ]; then
        CANDIDATE_COUNT=$(python3 -c "
import json
try:
    with open('$CANDIDATES_FILE', 'r') as f:
        candidates = json.load(f)
    print(len(candidates))
except:
    print(0)
")
        
        if [ "$CANDIDATE_COUNT" -gt 0 ]; then
            echo "[$TIMESTAMP] 📧 Sending watchlist email ($CANDIDATE_COUNT candidates)..." | tee -a "$LOG_FILE"
            
            EMAIL_CONTENT=$(python3 -c "
import sys
sys.path.append('$SCRIPT_DIR')
from qullamaggie.report import format_email_content
from qullamaggie.screen import Candidate
import json

# Load gate state
gate_file = '$TODAY_DIR/gate.json'
gate_state = {}
try:
    with open(gate_file, 'r') as f:
        gate_state = json.load(f)
except:
    pass

# Load candidates
candidates = []
try:
    with open('$CANDIDATES_FILE', 'r') as f:
        candidates_data = json.load(f)
        candidates = [Candidate(**c) for c in candidates_data]
except:
    pass

print(format_email_content(gate_state, candidates))
")
            
            if $QULLAMAGGIE_PY $EMAIL_SCRIPT "$RECIPIENT" "Qullamaggie Watchlist" "$EMAIL_CONTENT" 2>/dev/null; then
                echo "[$TIMESTAMP] 📧 Watchlist email sent" | tee -a "$LOG_FILE"
            else
                echo "[$TIMESTAMP] ❌ Watchlist email failed" | tee -a "$LOG_FILE"
            fi
        else
            echo "[$TIMESTAMP] No candidates found - no email sent" | tee -a "$LOG_FILE"
        fi
    fi

# ========================================
# POST-OPEN ANALYSIS (>= 9:35 AM)
# ========================================
elif [[ "$CURRENT_TIME" >= "$MARKET_OR_TIME" ]]; then
    echo "[$TIMESTAMP] ⚡ Running opening range analysis..." | tee -a "$LOG_FILE"
    
    OR_OUTPUT=$($QULLAMAGGIE_PY -m qullamaggie.run opening-range 2>&1) || {
        echo "[$TIMESTAMP] ❌ Opening range analysis failed: $OR_OUTPUT" | tee -a "$LOG_FILE"
        exit 1
    }
    
    echo "[$TIMESTAMP] ✅ Opening range analysis complete" | tee -a "$LOG_FILE"
    
    # Check for breakout signals
    TODAY_DIR="$ARTIFACTS_DIR/$(TZ='America/New_York' date '+%Y-%m-%d')"
    OR_FILE="$TODAY_DIR/opening_range.csv"
    
    if [ -f "$OR_FILE" ]; then
        TRIGGERED_COUNT=$(python3 -c "
import pandas as pd
try:
    df = pd.read_csv('$OR_FILE', index_col='symbol')
    triggered = df[df['entry_triggered'] == True]
    print(len(triggered))
except:
    print(0)
")
        
        if [ "$TRIGGERED_COUNT" -gt 0 ]; then
            echo "[$TIMESTAMP] 🚨 Opening range breakouts detected ($TRIGGERED_COUNT signals)!" | tee -a "$LOG_FILE"
            
            # Send breakout alert email
            BREAKOUT_CONTENT=$(python3 -c "
import sys
sys.path.append('$SCRIPT_DIR')
import pandas as pd
import json

# Load gate state
gate_file = '$TODAY_DIR/gate.json'
gate_state = {}
try:
    with open(gate_file, 'r') as f:
        gate_state = json.load(f)
except:
    pass

# Load candidates
candidates = []
candidates_file = '$TODAY_DIR/candidates.json'
try:
    with open(candidates_file, 'r') as f:
        candidates_data = json.load(f)
    from qullamaggie.screen import Candidate
    candidates = [Candidate(**c) for c in candidates_data]
except:
    pass

# Load opening range
or_df = None
try:
    or_df = pd.read_csv('$OR_FILE', index_col='symbol')
except:
    pass

from qullamaggie.report import format_email_content, opening_range_to_dataframe

# Convert opening range to dict format for email
or_results = {}
if or_df is not None:
    for symbol, row in or_df.iterrows():
        or_results[symbol] = {
            'orh': row['orh'],
            'orl': row['orl'],
            'last_price': row['last_price'],
            'entry_triggered': row['entry_triggered']
        }

print(format_email_content(gate_state, candidates, or_results))
")
            
            if $QULLAMAGGIE_PY $EMAIL_SCRIPT "$RECIPIENT" "Qullamaggie Breakouts" "$BREAKOUT_CONTENT" 2>/dev/null; then
                echo "[$TIMESTAMP] 📧 Breakout alert email sent" | tee -a "$LOG_FILE"
            else
                echo "[$TIMESTAMP] ❌ Breakout alert email failed" | tee -a "$LOG_FILE"
            fi
        else
            echo "[$TIMESTAMP] No opening range breakouts detected" | tee -a "$LOG_FILE"
        fi
    fi

# ========================================
# MARKET HOURS (9:30-9:34 AM)
# ========================================
else
    echo "[$TIMESTAMP] ⏳ Market just opened, waiting for opening range data..." | tee -a "$LOG_FILE"
    exit 0
fi

echo "[$TIMESTAMP] Qullamaggie analysis complete" | tee -a "$LOG_FILE"
