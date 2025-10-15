#!/usr/bin/env python3
"""
Comprehensive automated scanner, tweeter, and emailer.

Schedule:
- Weekdays (Mon-Fri): Scan stocks every 25 minutes (10:00 AM - 4:00 PM ET)
- Weekends (Sat-Sun): Scan crypto every 25 minutes (24/7)

Actions every 25 minutes:
1. Scan for signals
2. Pick the most volatile (or best available if none meet thresholds)
3. Tweet the signal
4. Email the signal
5. Save to database
"""
import os
import sys
import time
import subprocess
from datetime import datetime, time as dt_time, timedelta
from pathlib import Path
import pytz

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent.parent
SCAN_STOCKS_SCRIPT = SCRIPT_DIR / "compute_spike_params_stocks.py"
SCAN_CRYPTO_SCRIPT = SCRIPT_DIR / "compute_spike_params.py"
TWEET_SCRIPT = REPO_DIR / "x" / "scripts" / "tweet_with_limit.py"
EMAIL_SCRIPT = REPO_DIR / "gmail" / "scripts" / "send_email.py"
DB_SCRIPT = REPO_DIR / "database" / "log_signal.py"
VENV_PYTHON = SCRIPT_DIR / "venv" / "bin" / "python3"
X_VENV_PYTHON = REPO_DIR / "x" / "venv" / "bin" / "python3"
GMAIL_VENV_PYTHON = REPO_DIR / "gmail" / "venv" / "bin" / "python3"

SCAN_INTERVAL = 25 * 60  # 25 minutes in seconds

# Market hours (US Eastern Time) - for stocks only
STOCK_MARKET_OPEN = dt_time(10, 0)   # 10:00 AM ET
STOCK_MARKET_CLOSE = dt_time(16, 0)  # 4:00 PM ET
ET_TIMEZONE = pytz.timezone('America/New_York')

# Email recipient
EMAIL_RECIPIENT = os.getenv("INVESTOR_EMAIL_RECIPIENT", "deniz@bora.box")

def log(msg):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def is_weekday():
    """Check if today is a weekday (Mon-Fri)."""
    now_et = datetime.now(ET_TIMEZONE)
    return now_et.weekday() < 5

def is_within_stock_hours():
    """Check if current time is within stock market hours (10:00 AM - 4:00 PM ET, Mon-Fri)."""
    now_et = datetime.now(ET_TIMEZONE)
    
    # Must be weekday
    if now_et.weekday() >= 5:
        return False, "Weekend - scanning crypto instead"
    
    current_time = now_et.time()
    
    if current_time < STOCK_MARKET_OPEN:
        return False, f"Before stock hours (opens at 10:00 AM ET)"
    
    if current_time >= STOCK_MARKET_CLOSE:
        return False, f"After stock hours (closed at 4:00 PM ET)"
    
    return True, "Stock market hours"

def scan_stocks():
    """Run stock scanner and return signals."""
    try:
        result = subprocess.run(
            [str(VENV_PYTHON), str(SCAN_STOCKS_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=90
        )
        if result.returncode == 0 and result.stdout.strip():
            signals = [s.strip() for s in result.stdout.strip().split('\n') if s.strip()]
            return signals, "stock"
        return [], "stock"
    except Exception as e:
        log(f"Error scanning stocks: {e}")
        return [], "stock"

def scan_crypto():
    """Run crypto scanner and return signals."""
    try:
        result = subprocess.run(
            [str(VENV_PYTHON), str(SCAN_CRYPTO_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=90
        )
        if result.returncode == 0 and result.stdout.strip():
            signals = [s.strip() for s in result.stdout.strip().split('\n') if s.strip()]
            return signals, "crypto"
        return [], "crypto"
    except Exception as e:
        log(f"Error scanning crypto: {e}")
        return [], "crypto"

def parse_signal_metrics(signal):
    """Extract TR/ATR and Z-score from signal string for ranking."""
    import re
    
    # Format: $SYMBOL $PRICE ±X.XX% | X.XXx ATR | Z ±X.XX | Breakout
    tr_atr_match = re.search(r'(\d+\.\d+)x\s+ATR', signal)
    z_match = re.search(r'Z\s+([\-\+]?\d+\.\d+)', signal)
    pct_match = re.search(r'([\-\+]\d+\.\d+)%', signal)
    
    tr_atr = float(tr_atr_match.group(1)) if tr_atr_match else 0.0
    z_score = abs(float(z_match.group(1))) if z_match else 0.0
    pct_change = abs(float(pct_match.group(1))) if pct_match else 0.0
    
    # Volatility score: weighted combination
    volatility_score = (tr_atr * 0.4) + (z_score * 0.4) + (pct_change * 0.2)
    
    return volatility_score, tr_atr, z_score, pct_change

def select_best_signal(signals):
    """Select the most volatile signal, or best available if none meet thresholds."""
    if not signals:
        return None
    
    # Rank all signals by volatility score
    ranked = []
    for signal in signals:
        score, tr_atr, z_score, pct_change = parse_signal_metrics(signal)
        ranked.append((score, signal, tr_atr, z_score, pct_change))
    
    # Sort by score (highest first)
    ranked.sort(key=lambda x: x[0], reverse=True)
    
    best = ranked[0]
    best_signal = best[1]
    
        # Check if it meets thresholds (has "| Breakout" at the end)
        meets_threshold = best_signal.endswith("| Breakout")
    
    if meets_threshold:
        log(f"   ✅ Signal meets thresholds (TR/ATR={best[2]:.2f}, Z={best[3]:.2f}, %={best[4]:.2f})")
    else:
        log(f"   ℹ️  No signals meet thresholds - using best available (score={best[0]:.2f})")
    
    return best_signal

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
            log(f"   🐦 Tweeted successfully")
            return True
        else:
            error = result.stderr.strip()
            if "Rate limit reached" in error:
                log(f"   🚫 Twitter rate limit reached - skipping tweet")
            else:
                log(f"   ❌ Tweet failed: {error[:100]}")
            return False
    except Exception as e:
        log(f"   ❌ Error tweeting: {e}")
        return False

def email_signal(signal_text, asset_type):
    """Email a signal."""
    try:
        subject = f"Trading Signal - {asset_type.upper()}"
        result = subprocess.run(
            [str(GMAIL_VENV_PYTHON), str(EMAIL_SCRIPT), EMAIL_RECIPIENT, subject, signal_text],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            log(f"   ✉️  Emailed to {EMAIL_RECIPIENT}")
            return True
        else:
            log(f"   ❌ Email failed: {result.stderr.strip()[:100]}")
            return False
    except Exception as e:
        log(f"   ❌ Error emailing: {e}")
        return False

def save_to_database(signal_text, asset_type):
    """Save signal to database."""
    try:
        result = subprocess.run(
            [str(VENV_PYTHON), str(DB_SCRIPT), signal_text, asset_type],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            log(f"   💾 Saved to database")
            return True
        else:
            log(f"   ❌ Database save failed: {result.stderr.strip()[:100]}")
            return False
    except Exception as e:
        log(f"   ❌ Error saving to database: {e}")
        return False

def run_scan_cycle():
    """Execute one scan cycle - stocks on weekdays, crypto on weekends."""
    log("=" * 70)
    log("Starting 25-minute scan cycle...")
    
    # Determine what to scan
    if is_weekday():
        # Weekday - check if within stock market hours
        within_hours, reason = is_within_stock_hours()
        if not within_hours:
            log(f"⏸️  {reason}")
            return
        
        log("📊 Scanning STOCKS (weekday, market hours)")
        signals, asset_type = scan_stocks()
    else:
        # Weekend - scan crypto (24/7 market)
        log("🪙 Scanning CRYPTO (weekend)")
        signals, asset_type = scan_crypto()
    
    if not signals:
        log("   No data available - skipping cycle")
        return
    
    log(f"   Found {len(signals)} signal(s)")
    
    # Select best signal
    best_signal = select_best_signal(signals)
    
    if not best_signal:
        log("   No signals to process")
        return
    
    log(f"   📌 Selected: {best_signal[:80]}...")
    
    # Execute actions: Tweet, Email, Save
    tweet_signal(best_signal)
    email_signal(best_signal, asset_type)
    save_to_database(best_signal, asset_type)
    
    log("✅ Cycle complete")

def get_next_scan_time():
    """Calculate when the next scan should run."""
    now_et = datetime.now(ET_TIMEZONE)
    
    # If weekend, next scan is in 25 minutes (crypto runs 24/7)
    if now_et.weekday() >= 5:
        return now_et + timedelta(seconds=SCAN_INTERVAL)
    
    # If weekday, check if we're in stock market hours
    within_hours, _ = is_within_stock_hours()
    
    if within_hours:
        # In market hours - next scan in 25 minutes
        return now_et + timedelta(seconds=SCAN_INTERVAL)
    
    # Outside market hours on weekday
    current_time = now_et.time()
    
    if current_time < STOCK_MARKET_OPEN:
        # Before market open - wait until 10:00 AM
        next_scan = datetime.combine(now_et.date(), STOCK_MARKET_OPEN)
        next_scan = ET_TIMEZONE.localize(next_scan)
        return next_scan
    else:
        # After market close - wait until tomorrow 10:00 AM (or Monday if Friday)
        days_ahead = 3 if now_et.weekday() == 4 else 1  # Friday -> Monday
        next_date = now_et.date() + timedelta(days=days_ahead)
        next_scan = datetime.combine(next_date, STOCK_MARKET_OPEN)
        next_scan = ET_TIMEZONE.localize(next_scan)
        return next_scan

def main():
    """Main loop."""
    log("=" * 70)
    log("🚀 Automated Trading Bot v2.0 Started")
    log("=" * 70)
    log("Schedule:")
    log("  • Weekdays (Mon-Fri): Stocks every 25 min (10 AM - 4 PM ET)")
    log("  • Weekends (Sat-Sun): Crypto every 25 min (24/7)")
    log("")
    log("Actions every cycle:")
    log("  1. Scan for signals")
    log("  2. Select most volatile (or best available)")
    log("  3. Tweet signal")
    log("  4. Email signal")
    log("  5. Save to database")
    log("=" * 70)
    
    try:
        while True:
            now_et = datetime.now(ET_TIMEZONE)
            
            # Run scan cycle
            run_scan_cycle()
            
            # Calculate next scan time
            next_scan = get_next_scan_time()
            sleep_seconds = (next_scan - datetime.now(ET_TIMEZONE)).total_seconds()
            
            if sleep_seconds > 0:
                if sleep_seconds > 3600:
                    log(f"💤 Sleeping until {next_scan.strftime('%A, %B %d at %I:%M %p ET')} ({sleep_seconds/3600:.1f} hours)\n")
                else:
                    log(f"⏳ Next scan at {next_scan.strftime('%I:%M %p ET')} ({sleep_seconds/60:.0f} minutes)\n")
                
                time.sleep(sleep_seconds)
            
    except KeyboardInterrupt:
        log("\n👋 Shutting down...")
        sys.exit(0)
    except Exception as e:
        log(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

