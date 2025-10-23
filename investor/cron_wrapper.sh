#!/bin/bash
# Cron wrapper for investor.sh
# Ensures proper environment is loaded for cron execution

set -euo pipefail

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASYMMETRIC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Set up environment
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin"
export PYTHONPATH="$ASYMMETRIC_DIR/analyst/input/alpaca/venv/lib/python3.9/site-packages"

# Change to the investor directory
cd "$ASYMMETRIC_DIR/investor"

# Load environment variables
if [ -f "$ASYMMETRIC_DIR/analyst/config/api_keys.env" ]; then
    source "$ASYMMETRIC_DIR/analyst/config/api_keys.env"
fi

# Execute the actual script
exec ./investor.sh
