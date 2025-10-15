#!/usr/bin/env python3
"""Backward-compatible entrypoint for investor command execution."""

import sys
from pathlib import Path

# Ensure the `investor/` directory is on sys.path after the repo reorg.
REPO_ROOT = Path(__file__).resolve().parent
INVESTOR_DIR = REPO_ROOT / "investor"
if str(INVESTOR_DIR) not in sys.path:
    sys.path.insert(0, str(INVESTOR_DIR))

from investor_backend.executor import main

if __name__ == "__main__":
    raise SystemExit(main())
