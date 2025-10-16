#!/usr/bin/env python3
"""
Utility script to check and manage Twitter API rate limit status.
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add scripts to path
BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BASE_DIR / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))

from rate_limiter import get_rate_limiter


def print_status(limiter):
    """Print current rate limit status in a human-readable format."""
    status = limiter.get_status()
    
    print("=" * 70)
    print("Twitter API Rate Limit Status")
    print("=" * 70)
    print()
    
    print("Current Usage:")
    print(f"  Last 1 minute:  {status['calls_last_minute']:3d} / {status['limit_1_minute']:3d} calls  ({status['remaining_1_minute']:3d} remaining)")
    print(f"  Last 1 hour:    {status['calls_last_hour']:3d} / {status['limit_1_hour']:3d} calls  ({status['remaining_1_hour']:3d} remaining)")
    print(f"  Last 3 hours:   {status['calls_last_3_hours']:3d} / {status['limit_3_hours']:3d} calls  ({status['remaining_3_hours']:3d} remaining)")
    print()
    
    if 'rate_limited_until' in status:
        reset_dt = datetime.fromisoformat(status['rate_limited_until'])
        print(f"⚠️  Rate Limited Until: {reset_dt.strftime('%Y-%m-%d %H:%M:%S')} ({status['wait_seconds']}s)")
        print()
    
    # Traffic light indicator
    remaining_3h = status['remaining_3_hours']
    remaining_1h = status['remaining_1_hour']
    
    if 'rate_limited_until' in status:
        print("Status: 🔴 RATE LIMITED")
    elif remaining_1h < 5 or remaining_3h < 20:
        print("Status: 🟡 WARNING - Approaching limit")
    elif remaining_1h < 20 or remaining_3h < 50:
        print("Status: 🟠 CAUTION - Monitor usage")
    else:
        print("Status: 🟢 OK - Normal operation")
    
    print("=" * 70)


def print_json(limiter):
    """Print status as JSON."""
    status = limiter.get_status()
    print(json.dumps(status, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description='Twitter API Rate Limit Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python rate_limit_status.py             # Show current status
  python rate_limit_status.py --json      # Output as JSON
  python rate_limit_status.py --reset     # Reset rate limit state (use with caution!)
  python rate_limit_status.py --can-post  # Check if a post can be made right now
        """
    )
    
    parser.add_argument('--json', action='store_true',
                        help='Output status as JSON')
    parser.add_argument('--reset', action='store_true',
                        help='Reset rate limit state (use with caution!)')
    parser.add_argument('--can-post', action='store_true',
                        help='Check if a post can be made right now (exit code 0=yes, 1=no)')
    
    args = parser.parse_args()
    
    limiter = get_rate_limiter()
    
    if args.reset:
        confirm = input("Are you sure you want to reset rate limit state? (yes/no): ")
        if confirm.lower() in ['yes', 'y']:
            limiter.reset_state()
            print("✓ Rate limit state has been reset")
        else:
            print("Reset cancelled")
        return
    
    if args.can_post:
        can_proceed, reason = limiter.can_make_request()
        if can_proceed:
            print("✓ OK to post")
            sys.exit(0)
        else:
            print(f"✗ Cannot post: {reason}")
            sys.exit(1)
    
    if args.json:
        print_json(limiter)
    else:
        print_status(limiter)


if __name__ == '__main__':
    main()

