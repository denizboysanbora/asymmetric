#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

# Import the BTC fetcher
REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYST_DIR = REPO_ROOT / "analyst"
if str(ANALYST_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYST_DIR))

from fetch_btc_price import fetch_btc_usd, format_snapshot  # type: ignore

# Import the Gmail sender
GMAIL_DIR = REPO_ROOT / "output" / "gmail"
sys.path.insert(0, str(GMAIL_DIR / "scripts"))
sys.path.insert(0, str(GMAIL_DIR / "venv" / "lib" / "python3.14" / "site-packages"))
from send_email import send_email  # type: ignore


def main(to_email: str) -> int:
    snap = fetch_btc_usd()
    subject = "BTC Price Snapshot"
    body = format_snapshot(snap)
    send_email(to_email, subject, body)
    print(json.dumps({"success": True, "to": to_email, "body": body}))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: email_btc_snapshot.py you@example.com", flush=True)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))


