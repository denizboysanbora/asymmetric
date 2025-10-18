#!/bin/bash
# MCP-Enhanced Breakout Analyst
# Integrates Alpaca MCP server for real-time trading operations
# Schedule: 10 AM - 4 PM Eastern Time, weekdays, every 30 minutes

set -euo pipefail

# Process locking to prevent duplicate executions
LOCK_FILE="/tmp/mcp_breakout_analyst.lock"
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') MCP Breakout analyst already running (PID: $PID), skipping..." >> /Users/deniz/Code/asymmetric/analysts/breakout/logs/mcp_breakout_analyst.log
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
MCP_BREAKOUT_SCRIPT="$SCRIPT_DIR/mcp_breakout_scanner.py"
EMAIL_SCRIPT="$GMAIL_DIR/send_email.py"

# Recipient
RECIPIENT="deniz@bora.box"

# Log files
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/mcp_breakout_analyst.log"

# Timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] MCP-Enhanced Breakout analyst starting..." | tee -a "$LOG_FILE"

# Check if we're within operating hours (10 AM - 4 PM Eastern, weekdays)
CURRENT_HOUR=$(TZ='America/New_York' date '+%H')
CURRENT_DOW=$(TZ='America/New_York' date '+%u')  # 1=Monday, 7=Sunday
if [ "$CURRENT_HOUR" -lt 10 ] || [ "$CURRENT_HOUR" -ge 16 ] || [ "$CURRENT_DOW" -gt 5 ]; then
    echo "[$TIMESTAMP] Outside operating hours (10 AM - 4 PM ET, weekdays). Current hour: $CURRENT_HOUR, day: $CURRENT_DOW" | tee -a "$LOG_FILE"
    exit 0
fi

# ========================================
# MCP-ENHANCED BREAKOUT SCANNER
# ========================================
echo "[$TIMESTAMP] 🎯 Running MCP-enhanced breakout scanner..." | tee -a "$LOG_FILE"

# Run MCP scanner without auto-trading (safe mode)
MCP_OUTPUT=$($BREAKOUT_PY $MCP_BREAKOUT_SCRIPT --top-n 5 2>&1) || {
    echo "[$TIMESTAMP] ❌ MCP breakout scan failed: $MCP_OUTPUT" | tee -a "$LOG_FILE"
    MCP_OUTPUT=""
}

# Extract signals from output
MCP_SIGNALS=$(echo "$MCP_OUTPUT" | grep -v "Starting" | grep -v "Market Status" | grep -v "Buying Power" | grep -v "Analyzing" | grep -v "Found" | grep '^\$[A-Z0-9]' || true)

# Pick top breakout signal
TOP_MCP_SIGNAL=$(echo "$MCP_SIGNALS" | head -1)
MCP_SIGNAL_COUNT=$(echo "$MCP_SIGNALS" | wc -l)

if [ -n "$MCP_SIGNALS" ]; then
    echo "[$TIMESTAMP] 🎯 MCP Breakout setups detected!" | tee -a "$LOG_FILE"
    
    # Use the top breakout setup
    if [ -n "$TOP_MCP_SIGNAL" ]; then
        echo "[$TIMESTAMP] Selected MCP breakout: $TOP_MCP_SIGNAL" | tee -a "$LOG_FILE"
        
        # Determine signal type for email subject
        if echo "$TOP_MCP_SIGNAL" | grep -q "Flag Breakout"; then
            EMAIL_SUBJECT="MCP Flag Breakout Signal"
        elif echo "$TOP_MCP_SIGNAL" | grep -q "Range Breakout"; then
            EMAIL_SUBJECT="MCP Range Breakout Signal"
        else
            EMAIL_SUBJECT="MCP Breakout Signal"
        fi
        
        # Send email notification
        if $GMAIL_PY $EMAIL_SCRIPT "$RECIPIENT" "$EMAIL_SUBJECT" "$TOP_MCP_SIGNAL" 2>/dev/null; then
            echo "[$TIMESTAMP] 📧 Email sent: $TOP_MCP_SIGNAL" | tee -a "$LOG_FILE"
        else
            echo "[$TIMESTAMP] ❌ Email failed: $TOP_MCP_SIGNAL" | tee -a "$LOG_FILE"
        fi
        
        # Output to console
        echo "$TOP_MCP_SIGNAL"
    fi
else
    echo "[$TIMESTAMP] MCP Breakout: No setups found" | tee -a "$LOG_FILE"
fi

# ========================================
# AUTO-TRADING OPTION (UNCOMMENT TO ENABLE)
# ========================================
# Uncomment the following section to enable automatic trading
# WARNING: This will place real trades using your Alpaca account
# Make sure you understand the risks before enabling

# echo "[$TIMESTAMP] 🤖 Running MCP scanner with auto-trading..." | tee -a "$LOG_FILE"
# 
# AUTO_TRADE_OUTPUT=$($BREAKOUT_PY $MCP_BREAKOUT_SCRIPT --auto-trade --position-size 5.0 --top-n 1 2>&1) || {
#     echo "[$TIMESTAMP] ❌ Auto-trade scan failed: $AUTO_TRADE_OUTPUT" | tee -a "$LOG_FILE"
# }
# 
# # Check if any trades were executed
# if echo "$AUTO_TRADE_OUTPUT" | grep -q "Executed.*trades"; then
#     TRADE_INFO=$(echo "$AUTO_TRADE_OUTPUT" | grep "Placed.*shares" | tail -1)
#     echo "[$TIMESTAMP] ✅ $TRADE_INFO" | tee -a "$LOG_FILE"
#     
#     # Send trade notification email
#     if [ -n "$TRADE_INFO" ]; then
#         if $GMAIL_PY $EMAIL_SCRIPT "$RECIPIENT" "MCP Auto-Trade Executed" "$TRADE_INFO" 2>/dev/null; then
#             echo "[$TIMESTAMP] 📧 Trade notification email sent" | tee -a "$LOG_FILE"
#         fi
#     fi
# else
#     echo "[$TIMESTAMP] ℹ️  No auto-trades executed" | tee -a "$LOG_FILE"
# fi

echo "[$TIMESTAMP] MCP Breakout analyst analysis complete - Signals found: $MCP_SIGNAL_COUNT" | tee -a "$LOG_FILE"

