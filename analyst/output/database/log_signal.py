#!/usr/bin/env python3
"""
Log trading signals to database.
Usage: log_signal.py "$BTC $67,450 +2.45% | 2.25x ATR | Z 2.24 | Breakout" "crypto" "Breakout"
Usage: log_signal.py "$NVDA $183.15 +2.52%" "stock" "Trending"
"""
import sqlite3
import os
import sys
import re
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'signals.db')

def parse_signal(signal_text):
    """
    Parse signal format: $SYMBOL $PRICE ±X.XX% | X.XXx ATR | Z ±X.XX | Breakout
    or: $SYMBOL $PRICE ±X.XX%
    Returns: (symbol, price, change_pct, tr_atr, z_score, signal_type)
    """
    # Pattern for breakout: $SYMBOL $PRICE ±X.XX% | X.XXx ATR | Z ±X.XX | Breakout
    breakout_pattern = r'\$(\w+)\s+\$([0-9,]+(?:\.[0-9]+)?)\s+([\+\-][0-9\.]+)%\s+\|\s+([0-9\.]+)x\s+ATR\s+\|\s+Z\s+([\+\-]?[0-9\.]+)(?:\s+\|\s+([^|]+))?'
    
    # Pattern for trend: $SYMBOL $PRICE ±X.XX%
    trend_pattern = r'\$(\w+)\s+\$([0-9,]+(?:\.[0-9]+)?)\s+([\+\-][0-9\.]+)%'
    
    # Try breakout pattern first
    match = re.search(breakout_pattern, signal_text)
    if match:
        symbol = match.group(1)
        price_str = match.group(2).replace(',', '')
        price = float(price_str)
        change_pct = float(match.group(3))
        tr_atr = float(match.group(4))
        z_score = float(match.group(5))
        signal_type = match.group(6) if match.group(6) else 'Breakout'
        return (symbol, price, change_pct, tr_atr, z_score, signal_type)
    
    # Try trend pattern
    match = re.search(trend_pattern, signal_text)
    if match:
        symbol = match.group(1)
        price_str = match.group(2).replace(',', '')
        price = float(price_str)
        change_pct = float(match.group(3))
        # For trend signals, set tr_atr and z_score to 0
        tr_atr = 0.0
        z_score = 0.0
        signal_type = 'Trending'
        return (symbol, price, change_pct, tr_atr, z_score, signal_type)
    
    return None

def log_signal(signal_text, asset_class, signal_type_override=None):
    """Log signal to database."""
    parsed = parse_signal(signal_text)
    if not parsed:
        print(f"Error: Could not parse signal: {signal_text}", file=sys.stderr)
        return False
    
    symbol, price, change_pct, tr_atr, z_score, signal_type = parsed
    
    # Use override if provided
    if signal_type_override:
        signal_type = signal_type_override
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    local_timestamp = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        cursor.execute("""
            INSERT INTO signals 
            (timestamp, symbol, price, change_pct, tr_atr, z_score, signal_type, asset_class)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (local_timestamp, symbol, price, change_pct, tr_atr, z_score, signal_type, asset_class))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error logging signal: {e}", file=sys.stderr)
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: log_signal.py \"$SYMBOL $PRICE ...\" \"crypto|stock\" [signal_type]", file=sys.stderr)
        sys.exit(1)
    
    signal_text = sys.argv[1]
    asset_class = sys.argv[2]
    signal_type_override = sys.argv[3] if len(sys.argv) > 3 else None
    
    if log_signal(signal_text, asset_class, signal_type_override):
        print(f"✓ Logged: {signal_text[:50]}...")
    else:
        sys.exit(1)