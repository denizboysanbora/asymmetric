#!/bin/bash
# Email scan results for specific tickers
# Usage: ./email.sh AVGO

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
GMAIL_DIR="$REPO_DIR/gmail"
GMAIL_PY="$GMAIL_DIR/venv/bin/python3"
EMAIL_SCRIPT="$GMAIL_DIR/scripts/send_email.py"
RECIPIENT="deniz@bora.box"

# Get the signal output
SIGNAL=$("$SCRIPT_DIR/venv/bin/python3" "$SCRIPT_DIR/scan.py" "$@")

if [ -n "$SIGNAL" ]; then
    # Send each signal as separate email
    echo "$SIGNAL" | while IFS= read -r line; do
        "$GMAIL_PY" "$EMAIL_SCRIPT" "$RECIPIENT" "Signal" "$line"
        echo "📧 Emailed: $line"
    done
else
    echo "No signals to email" >&2
    exit 1
fi
