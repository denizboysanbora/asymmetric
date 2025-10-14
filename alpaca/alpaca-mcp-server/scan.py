#!/usr/bin/env python3
"""
Scan specific tickers and show/email/tweet in Investor format.
Usage: 
  scan AVGO TSLA     - Show in terminal
  email AVGO         - Email the output
  tweet AVGO         - Tweet the output
"""
import os
import sys
import subprocess
from datetime import datetime, timedelta
import numpy as np
from dotenv import load_dotenv
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestBarRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

# Import from main signal file to stay in sync
from compute_spike_params_stocks import classify_long_entry, format_signal_line

load_dotenv()

def analyze_symbol(symbol, client, now):
    """Analyze a single symbol."""
    # Get previous day's close
    yesterday = now - timedelta(days=1)
    daily_request = StockBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame(1, TimeFrameUnit.Day),
        start=yesterday - timedelta(days=3),
        end=yesterday
    )
    daily_bars = client.get_stock_bars(daily_request).data.get(symbol, [])
    
    if not daily_bars:
        return None
    
    prev_close = float(daily_bars[-1].close)
    
    # Get intraday bars for TR/ATR and Z-score calculation
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    intraday_request = StockBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame(5, TimeFrameUnit.Minute),
        start=market_open,
        end=now
    )
    bars = client.get_stock_bars(intraday_request).data.get(symbol, [])
    
    if len(bars) < 2:
        return None
    
    closes = np.array([float(b.close) for b in bars])
    rets = np.diff(np.log(closes))
    
    if len(rets) < 2:
        return None
    
    # TR/ATR
    tr_vals = []
    prev = float(bars[0].open)
    for b in bars:
        hi, lo, cl = float(b.high), float(b.low), float(b.close)
        tr = max(hi - lo, abs(hi - prev), abs(lo - prev))
        tr_vals.append(tr)
        prev = cl
    
    alpha = 2.0 / 15.0
    ema = None
    for tr in tr_vals:
        ema = tr if ema is None else alpha * tr + (1 - alpha) * ema
    tr_atr = tr_vals[-1] / ema if ema > 0 else float('nan')
    
    # Z-score
    mu = float(np.mean(rets[:-1]))
    sd = float(np.std(rets[:-1], ddof=1)) if len(rets) > 2 else float(np.std(rets[:-1]))
    z = (float(rets[-1]) - mu) / sd if sd > 1e-12 else 0.0
    
    # Get REAL-TIME current price from latest bar
    latest_request = StockLatestBarRequest(symbol_or_symbols=[symbol])
    latest_bars = client.get_stock_latest_bar(latest_request)
    
    if symbol in latest_bars:
        current_price = float(latest_bars[symbol].close)
    else:
        # Fallback to delayed data if latest bar not available
        current_price = closes[-1]
    
    # 24h move from previous close using real-time price
    dpp = ((current_price - prev_close) / prev_close) * 100.0
    
    # Classify using main signal logic (stays in sync with thresholds)
    sig = classify_long_entry(tr_atr, z, dpp, asset="stocks")
    
    return format_signal_line(symbol, current_price, dpp, tr_atr, z, sig)

def send_email(signal_text):
    """Send email using gmail script."""
    gmail_dir = "/Users/deniz/Library/CloudStorage/Dropbox/Bora/Code/box/investor/gmail"
    email_script = f"{gmail_dir}/scripts/send_email.py"
    gmail_py = f"{gmail_dir}/venv/bin/python3"
    recipient = "deniz@bora.box"
    
    try:
        subprocess.run([gmail_py, email_script, recipient, "Signal", signal_text], 
                      check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"Email error: {e}", file=sys.stderr)
        return False

def send_tweet(signal_text):
    """Send tweet using X script."""
    x_dir = "/Users/deniz/Library/CloudStorage/Dropbox/Bora/Code/box/investor/x"
    tweet_script = f"{x_dir}/scripts/tweet_with_limit.py"
    x_py = f"{x_dir}/venv/bin/python3"
    
    try:
        subprocess.run([x_py, tweet_script, signal_text], 
                      check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"Tweet error: {e}", file=sys.stderr)
        return False

def normalize_symbol(symbol):
    """Normalize symbol by removing $ and converting to uppercase."""
    return symbol.strip().replace('$', '').upper()

def main():
    if len(sys.argv) < 2:
        print("Usage:", file=sys.stderr)
        print("  scan.py SYMBOL1 SYMBOL2 ...  (show in terminal)", file=sys.stderr)
        print("Example:", file=sys.stderr)
        print("  scan.py AVGO", file=sys.stderr)
        print("  scan.py $AAPL $TSLA", file=sys.stderr)
        sys.exit(1)
    
    # Parse symbols (remove $ if present, strip whitespace)
    symbols = [normalize_symbol(s) for s in sys.argv[1:]]
    
    client = StockHistoricalDataClient(os.getenv('ALPACA_API_KEY'), os.getenv('ALPACA_SECRET_KEY'))
    now = datetime.now()
    
    # Analyze all symbols
    results = []
    for symbol in symbols:
        try:
            result = analyze_symbol(symbol, client, now)
            if result:
                results.append(result)
            else:
                print(f"${symbol}: No data available", file=sys.stderr)
        except Exception as e:
            print(f"${symbol}: Error - {e}", file=sys.stderr)
    
    # Output results
    for result in results:
        print(result)

if __name__ == "__main__":
    main()
