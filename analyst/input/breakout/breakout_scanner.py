#!/usr/bin/env python3
"""
Breakout Scanner - Detects volatility breakouts using technical analysis
Output format: $SYMBOL $PRICE +X.XX% | X.XXx ATR | Z X.XX | Breakout
"""
import os
import sys
import subprocess
from pathlib import Path

# Add alpaca directory to path
ALPACA_DIR = Path(__file__).parent.parent / "alpaca"
sys.path.insert(0, str(ALPACA_DIR))

def run_crypto_breakout_scan():
    """Run crypto breakout scan"""
    try:
        result = subprocess.run([
            str(ALPACA_DIR / "venv" / "bin" / "python3"),
            str(ALPACA_DIR / "compute_spike_params.py")
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Filter for breakout signals
            signals = []
            for line in result.stdout.split('\n'):
                if ' | Breakout' in line and line.strip():
                    signals.append(line.strip())
            return signals
        else:
            print(f"Crypto scan error: {result.stderr}", file=sys.stderr)
            return []
    except Exception as e:
        print(f"Crypto scan failed: {e}", file=sys.stderr)
        return []

def run_stock_breakout_scan():
    """Run stock breakout scan"""
    try:
        result = subprocess.run([
            str(ALPACA_DIR / "venv" / "bin" / "python3"),
            str(ALPACA_DIR / "compute_spike_params_stocks.py")
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Filter for breakout signals
            signals = []
            for line in result.stdout.split('\n'):
                if ' | Breakout' in line and line.strip():
                    signals.append(line.strip())
            return signals
        else:
            print(f"Stock scan error: {result.stderr}", file=sys.stderr)
            return []
    except Exception as e:
        print(f"Stock scan failed: {e}", file=sys.stderr)
        return []

def main():
    """Main breakout scanner"""
    print("🔍 Scanning for breakouts...", file=sys.stderr)
    
    # Run both scans
    crypto_signals = run_crypto_breakout_scan()
    stock_signals = run_stock_breakout_scan()
    
    # Output all signals
    all_signals = crypto_signals + stock_signals
    for signal in all_signals:
        print(signal)
    
    print(f"Found {len(all_signals)} breakout signals", file=sys.stderr)

if __name__ == "__main__":
    main()
