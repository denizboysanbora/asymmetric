#!/usr/bin/env python3
"""
Log trading signals to database.
Usage: log_signal.py "$NVDA $183.15 +2.52% | 45 RSI | 2.18x ATR | Z 2.45 | Breakout" "stock" "Breakout"
Usage: log_signal.py "$AAPL $150.25 +1.85% | 42 RSI | 1.95x ATR | Z 1.82 | Trend" "stock" "Trend"
"""
import os
import sys
import re
from datetime import datetime
import json
import requests

def parse_signal(signal_text):
    """
    Parse signal format: $SYMBOL $PRICE ±X.XX% | ## RSI | X.XXx ATR | Z ±X.XX | Breakout/Trend
    Returns: (symbol, price, change_pct, rsi, tr_atr, z_score, signal_type)
    """
    # Pattern for new format: $SYMBOL $PRICE ±X.XX% | ## RSI | X.XXx ATR | Z ±X.XX | Breakout/Trend
    new_pattern = r'\$(\w+)\s+\$([0-9,]+(?:\.[0-9]+)?)\s+([\+\-][0-9\.]+)%\s+\|\s+([0-9]+)\s+RSI\s+\|\s+([0-9\.]+)x\s+ATR\s+\|\s+Z\s+([\+\-]?[0-9\.]+)\s+\|\s+(Breakout|Trend)'
    
    # Try new pattern first
    match = re.search(new_pattern, signal_text)
    if match:
        symbol = match.group(1)
        price_str = match.group(2).replace(',', '')
        price = float(price_str)
        change_pct = float(match.group(3))
        rsi = float(match.group(4))
        tr_atr = float(match.group(5))
        z_score = float(match.group(6))
        signal_type = match.group(7)
        return (symbol, price, change_pct, rsi, tr_atr, z_score, signal_type)
    
    # Fallback to old patterns for backward compatibility
    # Pattern for old breakout: $SYMBOL $PRICE ±X.XX% | X.XXx ATR | Z ±X.XX | Breakout
    old_breakout_pattern = r'\$(\w+)\s+\$([0-9,]+(?:\.[0-9]+)?)\s+([\+\-][0-9\.]+)%\s+\|\s+([0-9\.]+)x\s+ATR\s+\|\s+Z\s+([\+\-]?[0-9\.]+)(?:\s+\|\s+([^|]+))?'
    
    # Pattern for old trend: $SYMBOL $PRICE ±X.XX%
    old_trend_pattern = r'\$(\w+)\s+\$([0-9,]+(?:\.[0-9]+)?)\s+([\+\-][0-9\.]+)%'
    
    # Try old breakout pattern
    match = re.search(old_breakout_pattern, signal_text)
    if match:
        symbol = match.group(1)
        price_str = match.group(2).replace(',', '')
        price = float(price_str)
        change_pct = float(match.group(3))
        tr_atr = float(match.group(4))
        z_score = float(match.group(5))
        signal_type = match.group(6) if match.group(6) else 'Breakout'
        rsi = 50.0  # Default RSI for old format
        return (symbol, price, change_pct, rsi, tr_atr, z_score, signal_type)
    
    # Try old trend pattern
    match = re.search(old_trend_pattern, signal_text)
    if match:
        symbol = match.group(1)
        price_str = match.group(2).replace(',', '')
        price = float(price_str)
        change_pct = float(match.group(3))
        # For old trend signals, set defaults
        tr_atr = 0.0
        z_score = 0.0
        rsi = 50.0
        signal_type = 'Trend'
        return (symbol, price, change_pct, rsi, tr_atr, z_score, signal_type)
    
    return None

def log_signal(signal_text, asset_class, signal_type_override=None):
    """Log signal to database."""
    parsed = parse_signal(signal_text)
    if not parsed:
        print(f"Error: Could not parse signal: {signal_text}", file=sys.stderr)
        return False
    
    symbol, price, change_pct, rsi, tr_atr, z_score, signal_type = parsed
    
    # Use override if provided
    if signal_type_override:
        signal_type = signal_type_override

    # Prepare row for DBs
    local_timestamp = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')
    row = {
        "timestamp": local_timestamp,
        "symbol": symbol,
        "price": float(price),
        "change_pct": float(change_pct),
        "rsi": float(rsi),
        "tr_atr": float(tr_atr),
        "z_score": float(z_score),
        "signal_type": str(signal_type),
        "asset_class": str(asset_class),
    }

    # Use Supabase as primary database
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_KEY")
    )
    
    if not supabase_url or not supabase_key:
        print("Error: Supabase configuration missing. Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.", file=sys.stderr)
        return False
    
    try:
        endpoint = supabase_url.rstrip('/') + "/rest/v1/signals"
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        resp = requests.post(endpoint, headers=headers, data=json.dumps(row), timeout=10)
        if 200 <= resp.status_code < 300:
            return True
        else:
            print(f"Supabase insert failed: {resp.status_code} {resp.text}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"Supabase insert error: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: log_signal.py \"$SYMBOL $PRICE ...\" \"stock\" [signal_type]", file=sys.stderr)
        sys.exit(1)
    
    signal_text = sys.argv[1]
    asset_class = sys.argv[2]
    signal_type_override = sys.argv[3] if len(sys.argv) > 3 else None
    
    if log_signal(signal_text, asset_class, signal_type_override):
        print(f"✓ Logged: {signal_text[:50]}...")
    else:
        sys.exit(1)