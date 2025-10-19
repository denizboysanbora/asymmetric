#!/usr/bin/env python3
"""
Build a real NASDAQ SQLite database using Alpaca market data or split existing data into monthly files.

Requirements:
- Env vars: ALPACA_API_KEY, ALPACA_SECRET_KEY, optional ALPACA_DATA_FEED (iex or sip) when pulling from Alpaca
- Date range: 2025-01-01 to 2025-10-17 (inclusive)
- Universe: All active, tradable NASDAQ US equities from Alpaca assets
- Stores: open, high, low, close, adjusted_close, volume, rsi(14), atr(14)

Notes:
- Batches symbols to respect rate limits
- Retries with exponential backoff on rate limits/network errors
- Upserts by (symbol, date) for resume-safe re-runs
- `--split-existing` copies rows from a legacy annual database into monthly databases without making API calls
"""
import argparse
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Alpaca
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass, AssetExchange, AssetStatus

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import Adjustment, DataFeed
from alpaca.common.exceptions import APIError

from db_manager import MonthKey, MonthlyDatabaseManager, ensure_directory


BASE_DIR = Path(__file__).parent
DB_DIR = ensure_directory(BASE_DIR / "nasdaq_db")
DB_MANAGER = MonthlyDatabaseManager(DB_DIR)
START_DATE = "2025-01-01"
END_DATE = "2025-10-17"
SYMBOL_CHUNK_SIZE = 200  # conservative; Alpaca supports multi-symbol requests
MAX_RETRIES = 6
BASE_BACKOFF_SECONDS = 2.0


def load_config() -> Tuple[str, str, str]:
    load_dotenv(dotenv_path=BASE_DIR / ".env")
    load_dotenv(dotenv_path=BASE_DIR.parent / ".env")

    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    data_feed = os.getenv("ALPACA_DATA_FEED", "iex")  # iex or sip

    if not api_key or not secret_key:
        raise RuntimeError("Missing ALPACA_API_KEY or ALPACA_SECRET_KEY in environment.")

    return api_key, secret_key, data_feed


def get_nasdaq_symbols(trading_client: TradingClient) -> List[str]:
    req = GetAssetsRequest(
        status=AssetStatus.ACTIVE,
        asset_class=AssetClass.US_EQUITY,
        exchange=AssetExchange.NASDAQ,
    )
    assets = trading_client.get_all_assets(req)

    symbols = []
    for a in assets:
        if getattr(a, "tradable", False) and getattr(a, "symbol", None):
            symbols.append(a.symbol)

    # Deduplicate and sort for stability
    symbols = sorted(set(symbols))
    return symbols


def chunk_list(items: List[str], chunk_size: int) -> List[List[str]]:
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.bfill().round(2)


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    high_low = df["high"] - df["low"]
    high_pc = (df["high"] - prev_close).abs()
    low_pc = (df["low"] - prev_close).abs()
    tr = pd.concat([high_low, high_pc, low_pc], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=period).mean()
    return atr.bfill().round(4)


def fetch_bars_with_retries(
    data_client: StockHistoricalDataClient,
    symbols: List[str],
    start: str,
    end: str,
    adjustment: Adjustment,
    feed: DataFeed,
) -> Optional[pd.DataFrame]:
    attempt = 0
    while True:
        try:
            req = StockBarsRequest(
                symbol_or_symbols=symbols,
                timeframe=TimeFrame.Day,
                start=start,
                end=end,
                adjustment=adjustment,
                feed=feed,
                limit=10000,
            )
            resp = data_client.get_stock_bars(req)
            df = resp.df  # MultiIndex: (symbol, timestamp)
            if df is None or df.empty:
                return pd.DataFrame()
            # Normalize
            df = df.reset_index()
            # Rename to columns [symbol, timestamp, open, high, low, close, volume, vwap, trade_count]
            df.rename(columns={"timestamp": "date"}, inplace=True)
            df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_convert("US/Eastern").dt.date
            return df
        except APIError as e:
            # Rate limit or server error
            attempt += 1
            if attempt > MAX_RETRIES:
                raise
            sleep_s = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
            time.sleep(sleep_s)
        except Exception:
            attempt += 1
            if attempt > MAX_RETRIES:
                raise
            sleep_s = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
            time.sleep(sleep_s)


def upsert_prices(df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0

    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["year"] = df["date"].apply(lambda d: d.year)
    df["month"] = df["date"].apply(lambda d: d.month)

    inserted = 0
    for (year, month), group in df.groupby(["year", "month"]):
        key = MonthKey(year=year, month=month)
        conn = DB_MANAGER.connect_for_month(key)
        try:
            cur = conn.cursor()
            records = [
                (
                    row["symbol"],
                    row["date"].isoformat(),
                    float(row["open"]),
                    float(row["high"]),
                    float(row["low"]),
                    float(row["close"]),
                    int(row["volume"]),
                    float(row.get("adjusted_close", row["close"])),
                    float(row.get("rsi", np.nan)) if not pd.isna(row.get("rsi", np.nan)) else None,
                    float(row.get("atr", np.nan)) if not pd.isna(row.get("atr", np.nan)) else None,
                )
                for _, row in group.iterrows()
            ]
            cur.executemany(
                """
                INSERT OR REPLACE INTO nasdaq_prices
                (symbol, date, open, high, low, close, volume, adjusted_close, rsi, atr)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                records,
            )
            conn.commit()
            inserted += len(records)
        finally:
            conn.close()

    df.drop(columns=["year", "month"], inplace=True)

    return inserted


def split_existing_database(source_path: Path) -> None:
    if not source_path.exists():
        print(f"Legacy database not found at {source_path}")
        return

    conn = sqlite3.connect(source_path)
    try:
        df = pd.read_sql("SELECT * FROM nasdaq_prices", conn, parse_dates=["date"])
    finally:
        conn.close()

    if df.empty:
        print("Legacy database contains no rows.")
        return

    df["date"] = pd.to_datetime(df["date"]).dt.date
    inserted = upsert_prices(df)
    print(f"Split {inserted:,} rows from {source_path.name} into monthly databases.")
    verify()


def process_and_store(
    data_client: StockHistoricalDataClient,
    symbols: List[str],
    start: str,
    end: str,
    adjustment: Adjustment,
    feed: DataFeed,
) -> Tuple[int, int]:
    total_rows = 0
    total_symbols = 0
    for idx, chunk in enumerate(chunk_list(symbols, SYMBOL_CHUNK_SIZE), start=1):
        df = fetch_bars_with_retries(data_client, chunk, start, end, adjustment, feed)
        if df is None or df.empty:
            continue

        # Compute indicators per symbol
        dfs = []
        for symbol, g in df.groupby("symbol", sort=False):
            g = g.sort_values("date").copy()
            g["rsi"] = compute_rsi(g["close"], period=14)
            g["atr"] = compute_atr(g, period=14)
            # adjusted_close: if adjustment is provided, Alpaca returns adjusted "close"; store it separately as adjusted_close
            g["adjusted_close"] = g["close"]
            dfs.append(g)

        out = pd.concat(dfs, ignore_index=True)
        inserted = upsert_prices(out)
        total_rows += inserted
        total_symbols += len(chunk)
        # Gentle pacing between chunks to respect rate limits
        time.sleep(0.5)
    return total_symbols, total_rows


def verify() -> None:
    summaries = DB_MANAGER.summarize()
    total_rows = sum(item[1] for item in summaries)
    first_dates = [item[2] for item in summaries if item[2]]
    last_dates = [item[3] for item in summaries if item[3]]
    if not summaries:
        print("No database files found.")
        return

    print(f"Total rows: {total_rows:,}")
    if first_dates and last_dates:
        print(f"Date range: {min(first_dates)} -> {max(last_dates)}")

    for path, count, first, last in summaries:
        print(f" - {path.name}: {count:,} rows ({first} -> {last})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or split NASDAQ SQLite databases.")
    parser.add_argument(
        "--split-existing",
        action="store_true",
        help="Split the legacy annual database into monthly partitioned files without hitting the API.",
    )
    args = parser.parse_args()

    if args.split_existing:
        legacy_db_path = BASE_DIR / "nasdaq_2025.db"
        split_existing_database(legacy_db_path)
        return

    print("Building NASDAQ database from Alpaca (2025-01-01 .. 2025-10-17)")
    api_key, secret_key, data_feed = load_config()

    # Do not purge existing rows; allow resume-safe upserts

    trading_client = TradingClient(api_key, secret_key)
    data_client = StockHistoricalDataClient(api_key, secret_key)

    symbols = get_nasdaq_symbols(trading_client)
    if not symbols:
        raise RuntimeError("No NASDAQ symbols returned from Alpaca.")
    print(f"Total NASDAQ symbols: {len(symbols)}")

    start_time = time.time()
    adj = "all"  # request adjusted prices
    # Resolve feed enum
    feed_enum = DataFeed.IEX if str(data_feed).lower() == "iex" else DataFeed.SIP

    processed_symbols, inserted_rows = process_and_store(
        data_client=data_client,
        symbols=symbols,
        start=f"{START_DATE}T00:00:00Z",
        end=f"{END_DATE}T23:59:59Z",
        adjustment=Adjustment.ALL,
        feed=feed_enum,
    )
    took = time.time() - start_time
    print(f"Inserted rows: {inserted_rows:,} across {processed_symbols} symbols in {took:.1f}s")

    verify()


if __name__ == "__main__":
    main()
