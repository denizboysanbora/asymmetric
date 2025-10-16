#!/usr/bin/env python3
"""
Single-worker Twitter client with automatic rate limit handling.
Handles 429 and 5xx errors with retry logic.
Includes proactive rate limiting to prevent 429 errors.
"""
import os
import sys
import time
import random
import logging
from functools import wraps
from pathlib import Path

# Add imghdr shim to path (Python 3.12+ compatibility)
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

import tweepy
from dotenv import load_dotenv
from rate_limiter import get_rate_limiter

log = logging.getLogger("tw")
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


def _sleep_until(reset_epoch: int):
    """Sleep until rate limit reset time."""
    now = int(time.time())
    wait = max(reset_epoch - now, 0) + random.uniform(0.25, 0.75)
    log.warning(f"[429] sleeping {wait:.1f}s until reset={reset_epoch}")
    time.sleep(wait)


def retry_on_limits(fn):
    """Decorator: Retry on 429 (sleep to reset) and 5xx (exponential backoff + jitter)."""
    @wraps(fn)
    def run(*args, **kwargs):
        limiter = get_rate_limiter()
        backoff = 1.6
        tries = 0
        while True:
            try:
                # Proactive rate limit check before making the request
                can_proceed, reason = limiter.can_make_request()
                if not can_proceed:
                    log.warning(f"Rate limit check failed: {reason}")
                    # Wait up to 5 minutes for rate limit to clear
                    if not limiter.wait_if_needed(max_wait_seconds=300):
                        raise Exception(f"Rate limit exceeded: {reason}")
                
                # Make the request
                result = fn(*args, **kwargs)
                
                # Record successful API call
                limiter.record_request()
                return result
                
            except tweepy.TooManyRequests as e:
                # Record the 429 error
                reset = 0
                try:
                    reset = int(e.response.headers.get("x-rate-limit-reset", "0"))
                except Exception:
                    pass
                if reset <= 0:
                    reset = int(time.time()) + 15 * 60  # fallback 15min
                
                limiter.record_429(reset)
                _sleep_until(reset)
                tries = 0
                
            except tweepy.TwitterServerError:
                delay = min(60, backoff ** tries) + random.uniform(0, 0.5)
                log.warning(f"[5xx] retrying in {delay:.1f}s (attempt {tries+1})")
                time.sleep(delay)
                tries += 1
                if tries > 6:
                    raise
    return run


class TwitterClient:
    """Twitter client with automatic rate limit handling."""
    
    def __init__(self):
        # Load credentials from .env
        env_path = BASE_DIR / 'config' / '.env'
        load_dotenv(env_path)
        
        self.client = tweepy.Client(
            consumer_key=os.environ["X_API_KEY"],
            consumer_secret=os.environ["X_API_KEY_SECRET"],
            access_token=os.environ["X_ACCESS_TOKEN"],
            access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
            wait_on_rate_limit=False,  # custom logic handles waiting
        )
    
    @retry_on_limits
    def post_tweet(self, text: str):
        """Post a tweet with automatic retry on rate limits."""
        return self.client.create_tweet(text=text)
    
    @retry_on_limits
    def recent_search(self, query: str, max_results: int = 25):
        """Search recent tweets with automatic retry."""
        return self.client.search_recent_tweets(query=query, max_results=max_results)


if __name__ == "__main__":
    tw = TwitterClient()
    result = tw.post_tweet("Test tweet from crypto alerts system")
    print(result)

