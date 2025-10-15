#!/usr/bin/env python3
"""
Check whether the U.S. equity market is currently in its regular trading session.
Prints "open" or "closed" and exits 0 on success.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()


def market_status(now_utc: datetime) -> str:
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    if not api_key or not secret_key:
        raise RuntimeError("Missing ALPACA_API_KEY or ALPACA_SECRET_KEY environment variables.")

    client = TradingClient(api_key, secret_key, paper=True)

    # Get current market clock
    clock = client.get_clock()
    
    return "open" if clock.is_open else "closed"


def main() -> int:
    now_utc = datetime.now(timezone.utc)
    try:
        status = market_status(now_utc)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
