#!/usr/bin/env python3
"""Compatibility wrapper for legacy Trader tooling."""

import sys
from pathlib import Path

# Ensure the repository root is on sys.path so investor_backend is importable.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from investor_backend.executor import main  # noqa: E402  (import after sys.path tweak)

if __name__ == "__main__":
    raise SystemExit(main())
