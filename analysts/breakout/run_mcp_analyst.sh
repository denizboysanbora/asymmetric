#!/bin/bash
# Run Native MCP Analyst
# Fast and efficient breakout signal detection using MCP server

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASYMMETRIC_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Load environment variables
if [ -f "$ASYMMETRIC_DIR/analysts/config/api_keys.env" ]; then
    source "$ASYMMETRIC_DIR/analysts/config/api_keys.env"
fi

# Python executable
PYTHON_PATH="$ASYMMETRIC_DIR/analysts/input/alpaca/venv/bin/python3"
ANALYST_SCRIPT="$SCRIPT_DIR/mcp_analyst.py"

# Check if we're within operating hours (10 AM - 4 PM Eastern, weekdays)
CURRENT_HOUR=$(TZ='America/New_York' date '+%H')
CURRENT_DOW=$(TZ='America/New_York' date '+%u')  # 1=Monday, 7=Sunday

echo "🚀 Native MCP Analyst"
echo "===================="
echo "📅 Current Time: $(TZ='America/New_York' date '+%Y-%m-%d %H:%M:%S ET')"
echo "📊 Market Hours: 10 AM - 4 PM ET (Weekdays)"

if [ "$CURRENT_HOUR" -ge 10 ] && [ "$CURRENT_HOUR" -lt 16 ] && [ "$CURRENT_DOW" -le 5 ]; then
    echo "✅ Market is open - running analysis..."
else
    echo "⏰ Market is closed - running analysis anyway..."
fi

echo ""
echo "🔍 Scanning for breakout signals..."

# Run the analyst
$PYTHON_PATH $ANALYST_SCRIPT --max-stocks 30 --top-n 5

echo ""
echo "✅ Analysis complete!"

