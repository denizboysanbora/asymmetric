#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import urllib.request


def fetch_btc_usd() -> Dict[str, Any]:
    """
    Fetch live BTC/USD price from CoinDesk as a simple, unauthenticated source.
    Returns a dict with keys: price_usd (float), source, timestamp.
    """
    url = "https://api.coindesk.com/v1/bpi/currentprice/BTC.json"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    rate_float = float(data["bpi"]["USD"]["rate_float"])  # already numeric
    return {
        "symbol": "BTC",
        "price_usd": rate_float,
        "source": "coindesk",
        "timestamp": data.get("time", {}).get("updatedISO"),
    }


def format_snapshot(d: Dict[str, Any]) -> str:
    return f"$BTC price: ${d['price_usd']:.2f} (source: {d['source']}, at {d.get('timestamp')})"


def main() -> int:
    snap = fetch_btc_usd()
    print(json.dumps(snap))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


