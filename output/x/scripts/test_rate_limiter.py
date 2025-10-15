#!/usr/bin/env python3
"""
Test the tweet rate limiter logic
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

STATE_DIR = Path(__file__).parent.parent / "state"
STATE_FILE = STATE_DIR / "tweet_rate_limit.json"

def load_state():
    if not STATE_FILE.exists():
        return []
    with open(STATE_FILE, 'r') as f:
        data = json.load(f)
        return data.get('tweets', [])

def count_recent_tweets(tweets):
    cutoff = datetime.now() - timedelta(hours=24)
    cutoff_str = cutoff.isoformat()
    return len([t for t in tweets if t > cutoff_str])

# Test
tweets = load_state()
recent_count = count_recent_tweets(tweets)

print(f"Current tweet count in last 24h: {recent_count}/17")
print(f"Can send tweets: {'YES' if recent_count < 17 else 'NO (rate limit reached)'}")

if tweets:
    print(f"\nRecent tweet timestamps:")
    cutoff = datetime.now() - timedelta(hours=24)
    for ts in sorted(tweets, reverse=True)[:10]:
        dt = datetime.fromisoformat(ts)
        if dt > cutoff:
            age = datetime.now() - dt
            hours = age.total_seconds() / 3600
            print(f"  - {dt.strftime('%Y-%m-%d %H:%M:%S')} ({hours:.1f}h ago)")

