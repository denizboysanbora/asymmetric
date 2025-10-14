#!/usr/bin/env python3
"""
Log trading signals to database.
Usage: log_signal.py "$BTC $67,450 +2.45% | 2.25x ATR | Z 2.24 | L" "crypto"
"""
import sqlite3
import os
import sys
import re
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'signals.db')

def parse_signal(signal_text):
    """
    Parse signal format: $SYMBOL $PRICE ±X.XX% | X.XXx ATR | Z ±X.XX | L
    Returns: (symbol, price, change_pct, tr_atr, z_score, signal_type)
    """
    # Pattern: $SYMBOL $PRICE ±X.XX% | X.XXx ATR | Z ±X.XX | L
    # Note: Z score can be positive or negative with optional space after Z
    pattern = r'\$(\w+)\s+\$([0-9,]+(?:\.[0-9]+)?)\s+([\+\-][0-9\.]+)%\s+\|\s+([0-9\.]+)x\s+ATR\s+\|\s+Z\s+([\+\-]?[0-9\.]+)(?:\s+\|\s+([LS]))?'
    
    match = re.search(pattern, signal_text)
    if not match:
        return None
    
    symbol = match.group(1)
    price_str = match.group(2).replace(',', '')
    price = float(price_str)
    change_pct = float(match.group(3))
    tr_atr = float(match.group(4))
    z_score = float(match.group(5))
    signal_type = match.group(6) if match.group(6) else ''
    
    return (symbol, price, change_pct, tr_atr, z_score, signal_type)

def log_signal(signal_text, asset_class):
    """Log signal to database."""
    parsed = parse_signal(signal_text)
    if not parsed:
        print(f"Error: Could not parse signal: {signal_text}", file=sys.stderr)
        return False
    
    symbol, price, change_pct, tr_atr, z_score, signal_type = parsed
    
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
        print("Usage: log_signal.py \"$SYMBOL $PRICE ...\" \"crypto|stock\"", file=sys.stderr)
        sys.exit(1)
    
    signal_text = sys.argv[1]
    asset_class = sys.argv[2]
    
    if log_signal(signal_text, asset_class):
        print(f"✓ Logged: {signal_text[:50]}...")
    else:
        sys.exit(1)
