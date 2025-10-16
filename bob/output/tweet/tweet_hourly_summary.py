#!/usr/bin/env python3
"""
Queue signals for hourly tweet summaries between 08:00–24:00 local time.
Respects the 17 tweets / 24h limit by delegating to tweet_with_limit.py.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_DIR = BASE_DIR / "state"
STATE_FILE = STATE_DIR / "hourly_tweet_queue.json"
TWEET_LIMIT_SCRIPT = BASE_DIR / "scripts" / "tweet_with_limit.py"

# Tweet window (inclusive start hour, exclusive end hour) in local time
TWEET_WINDOW_START = 8   # 08:00 local
TWEET_WINDOW_END = 24    # midnight
MAX_SIGNALS_PER_TWEET = 5   # Limit the number of signals summarized per hour


@dataclass
class QueueState:
    entries: List[Dict[str, Any]]
    last_flushed: Optional[str]

    @classmethod
    def from_file(cls) -> "QueueState":
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text())
                return cls(entries=data.get("entries", []), last_flushed=data.get("last_flushed"))
            except json.JSONDecodeError:
                pass
        return cls(entries=[], last_flushed=None)

    def save(self) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps({
            "entries": self.entries,
            "last_flushed": self.last_flushed,
        }, indent=2))


def now_local() -> datetime:
    return datetime.now().astimezone()


def parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts).astimezone()


def prune_entries(state: QueueState, cutoff: datetime) -> None:
    state.entries = [e for e in state.entries if parse_iso(e["timestamp"]) >= cutoff]


def add_signals(state: QueueState, signals: List[str], asset: str) -> None:
    timestamp = now_local().isoformat()
    for signal in signals:
        state.entries.append({
            "timestamp": timestamp,
            "signal": signal,
            "asset": asset,
        })
    # Keep only the last 48 hours worth of data to avoid unbounded growth.
    prune_entries(state, now_local() - timedelta(hours=48))


def unique_preserve(items: List[str]) -> List[str]:
    seen = set()
    ordered = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def summarise_lines(lines: List[str]) -> str:
    if not lines:
        return ""
    uniq = unique_preserve(lines)
    text = "; ".join(uniq)
    if len(text) <= 200:
        return text
    text = "; ".join(uniq[:2])
    remaining = len(uniq) - 2
    if remaining > 0:
        text += f"; +{remaining} more"
    return text


def format_time_label(dt: datetime) -> str:
    label = dt.strftime("%I:%M%p")
    return label.lstrip("0")


def compose_summary(
    period_start: datetime,
    period_end: datetime,
    stock_lines: List[str],
    *,
    overflow_total: int = 0,
) -> str:
    tz_abbr = period_end.tzname() or "ET"
    window_label = f"{format_time_label(period_start)}–{format_time_label(period_end)} {tz_abbr} signals"
    sections = []
    stock_summary = summarise_lines(stock_lines)
    if stock_summary:
        sections.append(f"Stocks: {stock_summary}")

    if overflow_total > 0:
        sections.append(f"+{overflow_total} additional signal(s) not tweeted")

    if not sections:
        return ""

    summary = window_label + "\n" + "\n".join(sections)
    if len(summary) <= 275:
        return summary

    # Fallback to counts if the text is too long.
    return (
        f"{window_label}\n"
        f"Stocks: {len(stock_lines)} signal(s)"
    )


def _extract_change_pct(line: str) -> Optional[float]:
    """Extract the first percentage value found in a signal line.
    Returns signed float (e.g., +2.33 -> 2.33, -0.42 -> -0.42) or None.
    """
    m = re.search(r"([+\-]?\d+(?:\.\d+)?)%", line)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def pick_most_extreme(lines: List[str]) -> Optional[str]:
    """Pick the single line with the largest absolute percentage move.
    Falls back to the first line if no percentages are found.
    """
    if not lines:
        return None
    best_line = None
    best_abs = -1.0
    for line in lines:
        pct = _extract_change_pct(line)
        if pct is None:
            continue
        val = abs(pct)
        if val > best_abs:
            best_abs = val
            best_line = line
    return best_line if best_line is not None else lines[0]


def send_summary(summary_text: str) -> bool:
    if not summary_text:
        return False
    result = subprocess.run(
        [sys.executable, str(TWEET_LIMIT_SCRIPT), summary_text],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr.strip() or "Tweet failed", file=sys.stderr)
        return False
    return True


def flush_if_ready(state: QueueState) -> None:
    now = now_local()
    current_hour_start = now.replace(minute=0, second=0, microsecond=0)
    previous_hour_start = current_hour_start - timedelta(hours=1)

    last_flushed = parse_iso(state.last_flushed) if state.last_flushed else previous_hour_start

    # Determine if we should send a tweet at this run.
    within_window = TWEET_WINDOW_START <= now.hour < TWEET_WINDOW_END
    at_top_of_hour = now.minute == 0

    # Always prune entries beyond 48h.
    prune_entries(state, now - timedelta(hours=48))

    if not at_top_of_hour:
        return

    # Determine which entries are ready for summary (between last flush and current hour start).
    ready_entries = []
    for entry in state.entries:
        ts = parse_iso(entry["timestamp"])
        if last_flushed <= ts < current_hour_start:
            ready_entries.append(entry)

    if not within_window:
        # Update last flushed boundary to avoid reprocessing old signals, but do not tweet.
        state.last_flushed = current_hour_start.isoformat()
        # Remove entries we have acknowledged.
        state.entries = [e for e in state.entries if e not in ready_entries]
        return

    if not ready_entries:
        state.last_flushed = current_hour_start.isoformat()
        return

    # Select a single most extreme move (by absolute percentage) among all ready entries.
    all_lines = [e["signal"] for e in ready_entries]
    summary_text = pick_most_extreme(all_lines) or ""

    if send_summary(summary_text):
        state.last_flushed = current_hour_start.isoformat()
        # Remove flushed entries
        state.entries = [e for e in state.entries if e not in ready_entries]
    else:
        # Keep entries for retry on next run.
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Queue signals for hourly tweet summaries.")
    parser.add_argument("--asset", choices=["stock"], help="Asset class of signals being added.")
    parser.add_argument("--add", nargs="+", help="Signal lines to add to the queue.")
    parser.add_argument("--flush", action="store_true", help="Force a flush attempt regardless of timing (respects window).")
    args = parser.parse_args()

    state = QueueState.from_file()

    if args.add:
        if not args.asset:
            parser.error("--asset is required when using --add")
        add_signals(state, args.add, args.asset)

    if args.flush or not args.add:
        flush_if_ready(state)

    state.save()


if __name__ == "__main__":
    main()
