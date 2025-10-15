#!/usr/bin/env python3
"""
Automatic 5-minute scanner and tweeter.
Runs continuously, scans for signals every 5 minutes during market hours only.
Market Hours: 9:30 AM - 4:00 PM ET, Monday-Friday
"""
import os
import sys
import time
import subprocess
from datetime import datetime, time as dt_time
from pathlib import Path
import pytz

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent.parent
SCAN_SCRIPT = SCRIPT_DIR / "compute_spike_params_stocks.py"
CHECK_MARKET_SCRIPT = SCRIPT_DIR / "check_market_open.py"
TWEET_SCRIPT = REPO_DIR / "x" / "scripts" / "tweet_with_limit.py"
VENV_PYTHON = SCRIPT_DIR / "venv" / "bin" / "python3"
X_VENV_PYTHON = REPO_DIR / "x" / "venv" / "bin" / "python3"

SCAN_INTERVAL = 300  # 5 minutes in seconds

# Market hours (US Eastern Time)
MARKET_OPEN_TIME = dt_time(9, 30)   # 9:30 AM ET
MARKET_CLOSE_TIME = dt_time(16, 0)  # 4:00 PM ET
ET_TIMEZONE = pytz.timezone('America/New_York')

def log(msg):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def is_within_market_hours():
    """Check if current time is within market hours (9:30 AM - 4:00 PM ET, Mon-Fri)."""
    now_et = datetime.now(ET_TIMEZONE)
    
    # Check if it's a weekday (Monday=0, Sunday=6)
    if now_et.weekday() >= 5:  # Saturday or Sunday
        return False, f"Weekend ({now_et.strftime('%A')})"
    
    current_time = now_et.time()
    
    if current_time < MARKET_OPEN_TIME:
        opens_in = datetime.combine(now_et.date(), MARKET_OPEN_TIME) - datetime.combine(now_et.date(), current_time)
        return False, f"Before market open (opens in {opens_in})"
    
    if current_time >= MARKET_CLOSE_TIME:
        return False, f"After market close (closed at 4:00 PM ET)"
    
    return True, "Market hours"

def is_market_open():
    """Check if market is currently open."""
    try:
        result = subprocess.run(
            [str(VENV_PYTHON), str(CHECK_MARKET_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            status = result.stdout.strip()
            return status == "open"
        return False
    except Exception as e:
        log(f"Error checking market status: {e}")
        return False

def scan_for_signals():
    """Run the signal scanner and return output."""
    try:
        result = subprocess.run(
            [str(VENV_PYTHON), str(SCAN_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')
        return []
    except Exception as e:
        log(f"Error scanning for signals: {e}")
        return []

def tweet_signal(signal_text):
    """Tweet a signal using the rate-limited tweet script."""
    try:
        result = subprocess.run(
            [str(X_VENV_PYTHON), str(TWEET_SCRIPT), signal_text],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            log(f"✅ Tweeted: {signal_text[:80]}...")
            return True
        else:
            error = result.stderr.strip()
            if "Rate limit reached" in error:
                log(f"🚫 Rate limit reached - skipping tweet")
            else:
                log(f"❌ Tweet failed: {error[:100]}")
            return False
    except Exception as e:
        log(f"Error tweeting signal: {e}")
        return False

def run_scan_cycle():
    """Execute one scan cycle."""
    log("Starting scan cycle...")
    
    # First check if we're within market hours (time-based check)
    within_hours, reason = is_within_market_hours()
    if not within_hours:
        log(f"⏸️  Outside market hours: {reason}")
        return
    
    # Then verify market is actually open (API check for holidays)
    if not is_market_open():
        log("⏸️  Market is closed (holiday or special closure)")
        return
    
    log("📊 Market is open - scanning for signals...")
    
    # Scan for signals
    signals = scan_for_signals()
    
    if not signals:
        log("No signals found")
        return
    
    log(f"Found {len(signals)} signal(s):")
    for signal in signals:
        log(f"  • {signal}")
    
    # Tweet each signal
    for signal in signals:
        if signal.strip():  # Skip empty lines
            tweet_signal(signal)
            time.sleep(2)  # Small delay between tweets

def get_next_market_open():
    """Calculate when market opens next."""
    now_et = datetime.now(ET_TIMEZONE)
    
    # If it's a weekday before market open
    if now_et.weekday() < 5 and now_et.time() < MARKET_OPEN_TIME:
        next_open = datetime.combine(now_et.date(), MARKET_OPEN_TIME)
        next_open = ET_TIMEZONE.localize(next_open)
        return next_open
    
    # Otherwise, next market open is tomorrow (or Monday if weekend)
    days_ahead = 1
    if now_et.weekday() == 4:  # Friday
        days_ahead = 3
    elif now_et.weekday() == 5:  # Saturday
        days_ahead = 2
    
    next_date = now_et.date() + __import__('datetime').timedelta(days=days_ahead)
    next_open = datetime.combine(next_date, MARKET_OPEN_TIME)
    next_open = ET_TIMEZONE.localize(next_open)
    return next_open

def main():
    """Main loop - only scans during market hours."""
    log("=" * 70)
    log("🚀 Auto-Scanner & Tweeter Started")
    log(f"Scan interval: {SCAN_INTERVAL} seconds (5 minutes)")
    log(f"Market hours: 9:30 AM - 4:00 PM ET (Mon-Fri)")
    log(f"Scan script: {SCAN_SCRIPT}")
    log(f"Tweet script: {TWEET_SCRIPT}")
    log("=" * 70)
    
    try:
        while True:
            within_hours, reason = is_within_market_hours()
            
            if within_hours:
                # We're in market hours - scan normally
                run_scan_cycle()
                log(f"⏳ Waiting {SCAN_INTERVAL} seconds until next scan...\n")
                time.sleep(SCAN_INTERVAL)
            else:
                # Outside market hours - calculate when to wake up
                next_open = get_next_market_open()
                now_et = datetime.now(ET_TIMEZONE)
                sleep_seconds = (next_open - now_et).total_seconds()
                
                if sleep_seconds > 3600:  # More than 1 hour away
                    log(f"💤 Outside market hours: {reason}")
                    log(f"   Next market open: {next_open.strftime('%A, %B %d at %I:%M %p ET')}")
                    log(f"   Sleeping until then ({sleep_seconds/3600:.1f} hours)...\n")
                    time.sleep(sleep_seconds)
                else:
                    # Less than 1 hour - check every 5 minutes
                    log(f"⏰ Market opens soon: {next_open.strftime('%I:%M %p ET')} (in {sleep_seconds/60:.0f} minutes)")
                    log(f"   Waiting {SCAN_INTERVAL} seconds...\n")
                    time.sleep(SCAN_INTERVAL)
                    
    except KeyboardInterrupt:
        log("\n👋 Shutting down...")
        sys.exit(0)
    except Exception as e:
        log(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

