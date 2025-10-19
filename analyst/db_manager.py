#!/usr/bin/env python3
"""Utilities for working with monthly-partitioned NASDAQ SQLite databases."""

from __future__ import annotations

import calendar
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Tuple

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS nasdaq_prices (
    symbol VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    adjusted_close DECIMAL(10,2),
    rsi DECIMAL(5,2),
    atr DECIMAL(10,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (symbol, date)
)
""".strip()

INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS idx_np_date ON nasdaq_prices(date)",
    "CREATE INDEX IF NOT EXISTS idx_np_symbol ON nasdaq_prices(symbol)",
    "CREATE INDEX IF NOT EXISTS idx_np_close ON nasdaq_prices(close)",
    "CREATE INDEX IF NOT EXISTS idx_np_rsi ON nasdaq_prices(rsi)",
    "CREATE INDEX IF NOT EXISTS idx_np_atr ON nasdaq_prices(atr)",
]

MONTH_NAME_TO_NUM = {abbr.lower(): idx for idx, abbr in enumerate(calendar.month_abbr) if abbr}


def _coerce_date(value: date | datetime | str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return datetime.strptime(value, "%Y-%m-%d").date()
    raise TypeError(f"Unsupported date value: {value!r}")


@dataclass(frozen=True)
class MonthKey:
    year: int
    month: int

    @property
    def label(self) -> str:
        month_abbr = calendar.month_abbr[self.month].lower()
        year_suffix = self.year % 100
        return f"{month_abbr}_{year_suffix:02d}"

    def first_day(self) -> date:
        return date(self.year, self.month, 1)


class MonthlyDatabaseManager:
    """Manages NASDAQ SQLite files partitioned by month."""

    def __init__(self, base_dir: Path | str, fallback_path: Optional[Path | str] = None):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.fallback_path = Path(fallback_path) if fallback_path else None

    def _month_key_from(self, value: date | datetime | str) -> MonthKey:
        coerced = _coerce_date(value)
        return MonthKey(coerced.year, coerced.month)

    def path_for_month(self, key: MonthKey) -> Path:
        return self.base_dir / f"nasdaq_{key.label}.db"

    def ensure_month(self, key: MonthKey) -> Path:
        path = self.path_for_month(key)
        need_init = not path.exists()
        conn = sqlite3.connect(path)
        try:
            cur = conn.cursor()
            cur.execute(SCHEMA_SQL)
            for stmt in INDEX_STATEMENTS:
                cur.execute(stmt)
            conn.commit()
        finally:
            conn.close()
        if need_init:
            path.touch(exist_ok=True)
        return path

    def connect_for_month(self, key: MonthKey) -> sqlite3.Connection:
        path = self.ensure_month(key)
        return sqlite3.connect(path)

    def _path_sort_key(self, path: Path) -> Tuple[int, int, str]:
        match = re.match(r"nasdaq_([a-z]{3})_(\d{2})\.db$", path.name)
        if match:
            month_token = match.group(1)
            month_num = MONTH_NAME_TO_NUM.get(month_token)
            if month_num:
                year_suffix = int(match.group(2))
                year = 2000 + year_suffix
                return (year, month_num, path.name)
        return (9999, 12, path.name)

    def list_monthly_paths(self) -> List[Path]:
        paths = list(self.base_dir.glob("nasdaq_*.db"))
        if self.fallback_path and self.fallback_path.exists():
            paths.append(self.fallback_path)
        if not paths:
            return []
        unique: List[Path] = []
        seen = set()
        for path in sorted(paths, key=self._path_sort_key):
            if path not in seen:
                unique.append(path)
                seen.add(path)
        return unique

    def month_keys_between(self, start: date | datetime | str, end: date | datetime | str) -> List[MonthKey]:
        start_date = _coerce_date(start)
        end_date = _coerce_date(end)
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        keys: List[MonthKey] = []
        cursor = date(start_date.year, start_date.month, 1)
        while cursor <= end_date:
            keys.append(MonthKey(cursor.year, cursor.month))
            if cursor.month == 12:
                cursor = date(cursor.year + 1, 1, 1)
            else:
                cursor = date(cursor.year, cursor.month + 1, 1)
        return keys

    def paths_between(self, start: date | datetime | str, end: date | datetime | str) -> List[Path]:
        keys = self.month_keys_between(start, end)
        paths: List[Path] = []
        for key in keys:
            path = self.path_for_month(key)
            if path.exists():
                paths.append(path)
        if self.fallback_path and self.fallback_path.exists():
            paths.append(self.fallback_path)
        if not paths:
            return []
        unique: List[Path] = []
        seen = set()
        for path in sorted(paths, key=self._path_sort_key):
            if path not in seen:
                unique.append(path)
                seen.add(path)
        return unique

    def latest_date(self) -> Optional[str]:
        latest: Optional[str] = None
        for path in self.list_monthly_paths():
            try:
                conn = sqlite3.connect(path)
                try:
                    row = conn.execute("SELECT MAX(date) FROM nasdaq_prices").fetchone()
                finally:
                    conn.close()
            except sqlite3.Error:
                continue
            if not row:
                continue
            value = row[0]
            if not value:
                continue
            if latest is None or value > latest:
                latest = value
        return latest

    def summarize(self) -> List[Tuple[Path, int, Optional[str], Optional[str]]]:
        summary = []
        for path in self.list_monthly_paths():
            try:
                conn = sqlite3.connect(path)
                try:
                    row = conn.execute(
                        "SELECT COUNT(*) as count, MIN(date) as first, MAX(date) as last FROM nasdaq_prices"
                    ).fetchone()
                finally:
                    conn.close()
            except sqlite3.Error:
                row = (0, None, None)
            summary.append((path, int(row[0]) if row else 0, row[1] if row else None, row[2] if row else None))
        return summary


def ensure_directory(path: Path | str) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target
