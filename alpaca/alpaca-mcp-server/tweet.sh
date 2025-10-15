#!/bin/bash
# Tweet scan results for specific tickers
# Usage: ./tweet.sh AVGO

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
X_DIR="$REPO_DIR/x"
X_PY="$X_DIR/venv/bin/python3"
TWEET_SCRIPT="$X_DIR/scripts/tweet_with_limit.py"

# Get the signal output
SIGNAL=$("$SCRIPT_DIR/venv/bin/python3" "$SCRIPT_DIR/scan.py" "$@")

if [ -n "$SIGNAL" ]; then
    # Tweet the signal(s)
    TWEET_OUTPUT=$("$X_PY" "$TWEET_SCRIPT" "$SIGNAL" 2>&1)
    
    if [ $? -eq 0 ]; then
        echo "🐦 Tweeted: $SIGNAL"
    elif echo "$TWEET_OUTPUT" | grep -q "Rate limit reached"; then
        echo "🚫 Rate limit reached (17 tweets/24h)" >&2
        exit 1
    else
        echo "⚠️  Tweet failed: $TWEET_OUTPUT" >&2
        exit 1
    fi
else
    echo "No signals to tweet" >&2
    exit 1
fi
