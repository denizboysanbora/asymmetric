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
from alpaca.trading.requests import GetCalendarRequest

load_dotenv()


def market_status(now_utc: datetime) -> str:
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    if not api_key or not secret_key:
        raise RuntimeError("Missing ALPACA_API_KEY or ALPACA_SECRET_KEY environment variables.")

    client = TradingClient(api_key, secret_key, paper=True)

    request = GetCalendarRequest(start=now_utc.date(), end=now_utc.date())
    calendar = client.get_calendar(request=request)
    if not calendar:
        return "closed"

    session = calendar[0]
    session_open = session.open.astimezone(timezone.utc)
    session_close = session.close.astimezone(timezone.utc)

    if session_open <= now_utc < session_close:
        return "open"

    return "closed"


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
