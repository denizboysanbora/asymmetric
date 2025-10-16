#!/usr/bin/env python3
"""
Centralized rate limiter for Twitter API to prevent 429 errors.
Uses a sliding window algorithm with persistent state.

Twitter API Limits:
- Tweet posting: 300 tweets per 3 hours (rolling window)
- We use conservative limits: 200 tweets per 3 hours to have buffer
"""
import json
import time
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import logging

BASE_DIR = Path(__file__).resolve().parents[1]
STATE_DIR = BASE_DIR / 'state'
RATE_LIMIT_STATE = STATE_DIR / 'rate_limit_state.json'

STATE_DIR.mkdir(parents=True, exist_ok=True)

# Rate limit configuration
MAX_TWEETS_PER_3H = 200  # Conservative limit (actual is 300)
MAX_TWEETS_PER_HOUR = 60  # Conservative limit
MAX_TWEETS_PER_MINUTE = 2  # Very conservative
WINDOW_3H_SECONDS = 3 * 60 * 60
WINDOW_1H_SECONDS = 60 * 60
WINDOW_1M_SECONDS = 60

log = logging.getLogger(__name__)


class RateLimiter:
    """Thread-safe rate limiter with persistent state."""
    
    def __init__(self):
        self.state_path = RATE_LIMIT_STATE
        self.api_calls: List[float] = []
        self.last_429_time: Optional[float] = None
        self.reset_time: Optional[float] = None
        self._load_state()
    
    def _load_state(self):
        """Load rate limit state from disk."""
        if self.state_path.exists():
            try:
                with open(self.state_path, 'r') as f:
                    data = json.load(f)
                    self.api_calls = data.get('api_calls', [])
                    self.last_429_time = data.get('last_429_time')
                    self.reset_time = data.get('reset_time')
                    
                    # Clean old calls (older than 3 hours)
                    cutoff = time.time() - WINDOW_3H_SECONDS
                    self.api_calls = [t for t in self.api_calls if t > cutoff]
            except Exception as e:
                log.warning(f"Failed to load rate limit state: {e}")
                self.api_calls = []
    
    def _save_state(self):
        """Persist rate limit state to disk."""
        try:
            data = {
                'api_calls': self.api_calls,
                'last_429_time': self.last_429_time,
                'reset_time': self.reset_time,
                'last_updated': time.time()
            }
            with open(self.state_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save rate limit state: {e}")
    
    def _clean_old_calls(self):
        """Remove API calls older than 3 hours."""
        cutoff = time.time() - WINDOW_3H_SECONDS
        self.api_calls = [t for t in self.api_calls if t > cutoff]
    
    def _get_calls_in_window(self, window_seconds: int) -> int:
        """Count API calls in the last N seconds."""
        self._clean_old_calls()
        cutoff = time.time() - window_seconds
        return sum(1 for t in self.api_calls if t > cutoff)
    
    def can_make_request(self, respect_429: bool = True) -> tuple[bool, Optional[str]]:
        """
        Check if we can make an API request without hitting rate limits.
        
        Returns:
            (can_proceed, reason_if_blocked)
        """
        now = time.time()
        
        # If we got a 429 recently and have a reset time, respect it
        if respect_429 and self.reset_time and now < self.reset_time:
            wait_seconds = int(self.reset_time - now)
            return False, f"Rate limited until {datetime.fromtimestamp(self.reset_time).strftime('%H:%M:%S')} ({wait_seconds}s)"
        
        # Check 3-hour window
        calls_3h = self._get_calls_in_window(WINDOW_3H_SECONDS)
        if calls_3h >= MAX_TWEETS_PER_3H:
            return False, f"3-hour limit reached ({calls_3h}/{MAX_TWEETS_PER_3H})"
        
        # Check 1-hour window
        calls_1h = self._get_calls_in_window(WINDOW_1H_SECONDS)
        if calls_1h >= MAX_TWEETS_PER_HOUR:
            return False, f"1-hour limit reached ({calls_1h}/{MAX_TWEETS_PER_HOUR})"
        
        # Check 1-minute window
        calls_1m = self._get_calls_in_window(WINDOW_1M_SECONDS)
        if calls_1m >= MAX_TWEETS_PER_MINUTE:
            return False, f"1-minute limit reached ({calls_1m}/{MAX_TWEETS_PER_MINUTE})"
        
        return True, None
    
    def wait_if_needed(self, max_wait_seconds: int = 300) -> bool:
        """
        Wait until we can make a request, up to max_wait_seconds.
        
        Returns:
            True if we can proceed, False if we hit max_wait
        """
        start = time.time()
        
        while True:
            can_proceed, reason = self.can_make_request()
            if can_proceed:
                return True
            
            elapsed = time.time() - start
            if elapsed >= max_wait_seconds:
                log.warning(f"Rate limit wait timeout after {elapsed:.0f}s: {reason}")
                return False
            
            # Wait a bit and retry
            wait_time = min(10, max_wait_seconds - elapsed)
            log.info(f"Rate limited ({reason}), waiting {wait_time:.0f}s...")
            time.sleep(wait_time)
    
    def record_request(self):
        """Record that we made an API request."""
        now = time.time()
        self.api_calls.append(now)
        self._clean_old_calls()
        self._save_state()
    
    def record_429(self, reset_timestamp: Optional[int] = None):
        """
        Record that we received a 429 error.
        
        Args:
            reset_timestamp: Unix timestamp when rate limit resets (from X-RateLimit-Reset header)
        """
        now = time.time()
        self.last_429_time = now
        
        if reset_timestamp:
            self.reset_time = float(reset_timestamp)
        else:
            # Conservative: wait 15 minutes if no reset time provided
            self.reset_time = now + (15 * 60)
        
        log.error(f"Rate limited (429). Reset at {datetime.fromtimestamp(self.reset_time).strftime('%Y-%m-%d %H:%M:%S')}")
        self._save_state()
    
    def get_status(self) -> Dict:
        """Get current rate limit status."""
        now = time.time()
        calls_1m = self._get_calls_in_window(WINDOW_1M_SECONDS)
        calls_1h = self._get_calls_in_window(WINDOW_1H_SECONDS)
        calls_3h = self._get_calls_in_window(WINDOW_3H_SECONDS)
        
        status = {
            'calls_last_minute': calls_1m,
            'calls_last_hour': calls_1h,
            'calls_last_3_hours': calls_3h,
            'limit_1_minute': MAX_TWEETS_PER_MINUTE,
            'limit_1_hour': MAX_TWEETS_PER_HOUR,
            'limit_3_hours': MAX_TWEETS_PER_3H,
            'remaining_1_minute': max(0, MAX_TWEETS_PER_MINUTE - calls_1m),
            'remaining_1_hour': max(0, MAX_TWEETS_PER_HOUR - calls_1h),
            'remaining_3_hours': max(0, MAX_TWEETS_PER_3H - calls_3h),
        }
        
        if self.reset_time and now < self.reset_time:
            status['rate_limited_until'] = datetime.fromtimestamp(self.reset_time).isoformat()
            status['wait_seconds'] = int(self.reset_time - now)
        
        return status
    
    def reset_state(self):
        """Reset rate limit state (use with caution)."""
        self.api_calls = []
        self.last_429_time = None
        self.reset_time = None
        self._save_state()
        log.info("Rate limit state reset")


# Global instance
_limiter = None

def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


if __name__ == '__main__':
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    limiter = get_rate_limiter()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        status = limiter.get_status()
        print(json.dumps(status, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == 'reset':
        limiter.reset_state()
        print("Rate limit state reset")
    else:
        print("Usage:")
        print("  python rate_limiter.py status  - Show current rate limit status")
        print("  python rate_limiter.py reset   - Reset rate limit state")

