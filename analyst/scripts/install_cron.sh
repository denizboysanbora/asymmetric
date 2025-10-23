#!/bin/bash
# Configure cron entries for the analyst breakout scanner and investor paper trader.
# Usage: ./scripts/install_cron.sh [--apply]

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BREAKOUT_SCRIPT="$ROOT_DIR/breakout/breakout_analyst.sh"
INVESTOR_SCRIPT="$ROOT_DIR/../investor/investor.sh"
LOG_DIR_BREAKOUT="$ROOT_DIR/breakout/logs"
LOG_DIR_INVESTOR="$ROOT_DIR/../investor/logs"

if [ ! -x "$BREAKOUT_SCRIPT" ]; then
    echo "❌ Breakout script not executable: $BREAKOUT_SCRIPT"
    echo "Run: chmod +x $BREAKOUT_SCRIPT"
    exit 1
fi

if [ ! -x "$INVESTOR_SCRIPT" ]; then
    echo "❌ Investor script not executable: $INVESTOR_SCRIPT"
    echo "Run: chmod +x $INVESTOR_SCRIPT"
    exit 1
fi

mkdir -p "$LOG_DIR_BREAKOUT" "$LOG_DIR_INVESTOR"

BREAKOUT_ENTRY="0,30 9-16 * * 1-5 cd $ROOT_DIR && $ROOT_DIR/input/alpaca/venv/bin/python3 enhanced_contraction_analysis.py >> $LOG_DIR_BREAKOUT/cron.log 2>&1"
INVESTOR_ENTRY="*/5 9-16 * * 1-5 $ROOT_DIR/../investor/cron_wrapper.sh >> $LOG_DIR_INVESTOR/cron.log 2>&1"

print_entries() {
    cat <<EOF
# Asymmetric automated trading tasks
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin

# Enhanced analyst: every 30 minutes between 9:00-16:59 ET (Mon-Fri) - 3 signal types
$BREAKOUT_ENTRY

# Investor paper trader: every 5 minutes between 10:00-15:59 ET (Mon-Fri)
$INVESTOR_ENTRY

# Daily database update: 6:00 PM ET weekdays
0 18 * * 1-5 cd $ROOT_DIR && $ROOT_DIR/input/alpaca/venv/bin/python3 final_database_update.py >> $ROOT_DIR/logs/daily_maintenance.log 2>&1
EOF
}

if [[ "${1:-}" == "--apply" ]]; then
    TMP_FILE="$(mktemp)"
    # Preserve existing cron entries except older asymmetric definitions
    crontab -l 2>/dev/null | grep -v "asymmetric/analyst/breakout/breakout_analyst.sh" | grep -v "asymmetric/investor/investor.sh" > "$TMP_FILE" || true
    print_entries >> "$TMP_FILE"
    crontab "$TMP_FILE"
    rm -f "$TMP_FILE"
    echo "✅ Cron entries installed. Verify with: crontab -l"
else
    echo "🚀 Proposed cron entries (pass --apply to install):"
    echo ""
    print_entries
fi
