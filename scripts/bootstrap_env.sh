#!/bin/bash
# Bootstrap the Python environment expected by the analyst and investor bots.
# Creates/updates the venv at analyst/input/alpaca/venv and installs dependencies.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/analyst/input/alpaca/venv"
REQUIREMENTS_FILE="$ROOT_DIR/requirements.txt"
PYTHON_EXEC=${PYTHON:-python3}

if ! command -v "$PYTHON_EXEC" >/dev/null 2>&1; then
    echo "❌ python3 not found. Install Python 3.10+ and rerun."
    exit 1
fi

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "❌ requirements.txt missing at $REQUIREMENTS_FILE"
    exit 1
fi

echo "📦 Using Python interpreter: $(command -v "$PYTHON_EXEC")"
echo "📁 Creating virtual environment at: $VENV_DIR"
"$PYTHON_EXEC" -m venv "$VENV_DIR"

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

echo "🐍 Upgrading pip/setuptools/wheel..."
"$VENV_PIP" install --upgrade pip setuptools wheel >/dev/null

echo "📚 Installing project dependencies..."
"$VENV_PIP" install -r "$REQUIREMENTS_FILE"

cat <<EOF
✅ Environment ready!
- Python: $VENV_PYTHON
- Packages: $(wc -l < "$REQUIREMENTS_FILE") listed in $REQUIREMENTS_FILE

Next steps:
1. Run Gmail auth (once): $VENV_PYTHON analyst/output/gmail/scripts/gmail_auth.py
2. Install cron jobs: ./scripts/install_cron.sh --apply
EOF
