#!/usr/bin/env python3
"""
Tweet rate limiter - enforces max 17 tweets per 24 hours
"""
import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
import subprocess

# Paths
BASE_DIR = Path(__file__).parent
STATE_DIR = BASE_DIR / "state"
STATE_FILE = STATE_DIR / "tweet_rate_limit.json"
TWEET_SCRIPT = BASE_DIR / "post_text_oauth1.py"

# Rate limit
MAX_TWEETS_PER_24H = 17

def load_state():
    """Load tweet timestamps from state file."""
    if not STATE_FILE.exists():
        return []
    try:
        with open(STATE_FILE, 'r') as f:
            data = json.load(f)
            return data.get('tweets', [])
    except:
        return []

def save_state(tweets):
    """Save tweet timestamps to state file."""
    STATE_DIR.mkdir(exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump({'tweets': tweets}, f, indent=2)

def clean_old_tweets(tweets):
    """Remove tweets older than 24 hours."""
    cutoff = datetime.now() - timedelta(hours=24)
    cutoff_str = cutoff.isoformat()
    return [t for t in tweets if t > cutoff_str]

def count_recent_tweets(tweets):
    """Count tweets in last 24 hours."""
    cutoff = datetime.now() - timedelta(hours=24)
    cutoff_str = cutoff.isoformat()
    return len([t for t in tweets if t > cutoff_str])

def send_tweet(text):
    """Send tweet using the original script."""
    result = subprocess.run(
        [sys.executable, str(TWEET_SCRIPT), text],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f'Tweet script error: {result.stderr}', file=sys.stderr)
    return result.returncode == 0

def main():
    if len(sys.argv) < 2:
        print('Usage: tweet_with_limit.py "tweet text"', file=sys.stderr)
        sys.exit(2)
    
    tweet_text = sys.argv[1]
    
    # Load and clean state
    tweets = load_state()
    tweets = clean_old_tweets(tweets)
    
    # Check rate limit
    recent_count = count_recent_tweets(tweets)
    
    if recent_count >= MAX_TWEETS_PER_24H:
        print(f'Rate limit reached: {recent_count}/{MAX_TWEETS_PER_24H} tweets in last 24h. Skipping tweet.', file=sys.stderr)
        sys.exit(1)
    
    # Send tweet
    if send_tweet(tweet_text):
        # Record timestamp
        now = datetime.now().isoformat()
        tweets.append(now)
        save_state(tweets)
        print(f'Tweet sent successfully. Count: {recent_count + 1}/{MAX_TWEETS_PER_24H} in last 24h', file=sys.stderr)
        sys.exit(0)
    else:
        print('Tweet failed to send', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()