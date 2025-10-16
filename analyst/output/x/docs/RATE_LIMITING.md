# Twitter API Rate Limiting

## Overview

This project now includes a comprehensive rate limiting system to prevent 429 (Too Many Requests) errors from the Twitter API. The system proactively checks rate limits before making API calls and coordinates across all scripts to ensure we stay within Twitter's limits.

## Twitter API Limits

Twitter enforces the following rate limits for tweet posting:
- **300 tweets per 3 hours** (rolling window)
- This translates to approximately **100 tweets per hour**

To provide a safety buffer, our system uses more conservative limits:
- **200 tweets per 3 hours**
- **60 tweets per hour**
- **2 tweets per minute**

## How It Works

### Centralized Rate Limiter

The `rate_limiter.py` module provides a centralized rate limiting system with:

1. **Persistent State**: Rate limit state is saved to `state/rate_limit_state.json`, so it persists across script invocations
2. **Sliding Window**: Tracks API calls using a sliding window algorithm for accurate rate limiting
3. **Proactive Checks**: Checks limits BEFORE making API calls to prevent 429 errors
4. **429 Handling**: Records 429 errors and respects the reset time provided by Twitter
5. **Thread-Safe**: Uses file-based state to coordinate across multiple processes

### Integration

All tweet posting scripts have been updated to use the rate limiter:
- `twitter_client.py` - Main Twitter client with retry logic
- `auto_tweet_crypto.py` - Crypto price movement tweets
- `tweet_btc_change.py` - BTC hourly change tweets
- `post_text_oauth1.py` - Manual tweet posting

Each script:
1. Checks rate limits before posting
2. Records successful API calls
3. Records 429 errors with reset times
4. Fails gracefully if rate limited

## Usage

### Checking Rate Limit Status

Use the rate limit status utility to check current usage:

```bash
# Show human-readable status
cd /Users/deniz/Library/CloudStorage/Dropbox/Bora/Code/asymmetric/x
./venv/bin/python scripts/rate_limit_status.py

# Output as JSON (useful for automation)
./venv/bin/python scripts/rate_limit_status.py --json

# Check if you can post right now (returns exit code 0 if OK)
./venv/bin/python scripts/rate_limit_status.py --can-post
```

Example output:
```
======================================================================
Twitter API Rate Limit Status
======================================================================

Current Usage:
  Last 1 minute:    1 /   2 calls  (  1 remaining)
  Last 1 hour:     12 /  60 calls  ( 48 remaining)
  Last 3 hours:    45 / 200 calls  (155 remaining)

Status: 🟢 OK - Normal operation
======================================================================
```

### Status Indicators

- 🟢 **OK** - Normal operation, plenty of capacity
- 🟠 **CAUTION** - Moderate usage, monitor
- 🟡 **WARNING** - Approaching limits
- 🔴 **RATE LIMITED** - Hit rate limit, waiting for reset

### Resetting Rate Limit State

If needed (e.g., after testing or if state gets corrupted):

```bash
./venv/bin/python scripts/rate_limit_status.py --reset
```

**Warning**: Only reset if you're certain the state is incorrect!

## Script Integration Examples

### For New Scripts

If you're creating a new script that posts tweets, integrate the rate limiter:

```python
from rate_limiter import get_rate_limiter

limiter = get_rate_limiter()

# Before posting a tweet
can_proceed, reason = limiter.can_make_request()
if not can_proceed:
    print(f"Rate limited: {reason}")
    return False

# Make your API call
# Use the helper from post_text_oauth1.py or requests directly
response = post_text(text)

# Record the successful call
if response.status_code == 201:
    limiter.record_request()
elif response.status_code == 429:
    # Record rate limit hit
    reset_time = response.headers.get('x-rate-limit-reset')
    limiter.record_429(reset_time)
```

### Waiting for Rate Limits

If you want to wait for rate limits to clear:

```python
from rate_limiter import get_rate_limiter

limiter = get_rate_limiter()

# Wait up to 5 minutes for rate limit to clear
if limiter.wait_if_needed(max_wait_seconds=300):
    # OK to proceed
    post_text(text)
    limiter.record_request()
else:
    # Still rate limited after max wait
    print("Rate limit timeout")
```

## Monitoring

### Log Files

Rate limiting events are logged in the scripts that use them. Check logs for:
- `Rate limit check failed:` - Proactive blocking
- `[429] sleeping` - Reactive handling of 429 errors
- `Rate limited until` - When limits will reset

### State File

The rate limit state is stored in:
```
/Users/deniz/Library/CloudStorage/Dropbox/Bora/Code/asymmetric/x/state/rate_limit_state.json
```

This file contains:
- Timestamps of recent API calls
- Last 429 error time
- Rate limit reset time

## Best Practices

1. **Always Check Before Posting**: Use `can_make_request()` before making API calls
2. **Record All API Calls**: Always call `record_request()` after successful posts
3. **Handle 429 Errors**: Call `record_429()` if you receive a 429 response
4. **Add Delays Between Tweets**: Use `time.sleep(5)` between multiple consecutive tweets
5. **Monitor Status**: Regularly check rate limit status, especially during high-volume periods
6. **Conservative Limits**: Our limits are set conservatively below Twitter's actual limits

## Troubleshooting

### Still Getting 429 Errors?

1. Check if multiple scripts are running simultaneously
2. Verify all scripts are using the rate limiter
3. Check the state file for accuracy
4. Consider reducing the rate limit thresholds in `rate_limiter.py`

### State File Issues

If the state file becomes corrupted:
```bash
rm /Users/deniz/Library/CloudStorage/Dropbox/Bora/Code/asymmetric/x/state/rate_limit_state.json
```

Or use the reset command:
```bash
./venv/bin/python scripts/rate_limit_status.py --reset
```

### Rate Limits Too Conservative?

Edit `rate_limiter.py` and adjust these constants:
```python
MAX_TWEETS_PER_3H = 200  # Increase if needed (max 300)
MAX_TWEETS_PER_HOUR = 60  # Increase if needed (max 100)
MAX_TWEETS_PER_MINUTE = 2  # Increase if needed
```

## Technical Details

### Sliding Window Algorithm

The rate limiter uses a sliding window algorithm that:
1. Stores timestamps of all API calls in the last 3 hours
2. Cleans up old timestamps beyond the window
3. Counts calls within each time window (1m, 1h, 3h)
4. Compares against limits before allowing new calls

### State Persistence

State is persisted to JSON after every:
- API call recording
- 429 error recording
- State cleanup

This ensures the rate limiter works correctly across:
- Multiple script invocations
- Crashed or interrupted scripts
- System restarts

### Rate Limit Reset

When a 429 error occurs, Twitter provides a reset timestamp via the `x-rate-limit-reset` header. The rate limiter:
1. Records this timestamp
2. Blocks all requests until the reset time
3. Automatically resumes after reset

## Support

For issues or questions about the rate limiting system, check:
1. This documentation
2. Rate limit status: `python scripts/rate_limit_status.py`
3. State file: `state/rate_limit_state.json`
4. Script logs for rate limiting messages
