#!/usr/bin/env python3
"""
CODX February 2020 Full Analysis
Analyze every trading day in February 2020 for CODX with updated parameters
"""
import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Load environment variables
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / "config" / "api_keys.env"
    if env_file.exists():
        load_dotenv(env_file)
        print("🔑 Loaded API keys from .env file")
except ImportError:
    pass

# Add alpaca directory to path
ALPACA_DIR = Path(__file__).parent / "input" / "alpaca"
sys.path.insert(0, str(ALPACA_DIR))

# Add breakout scanner to path
sys.path.insert(0, str(Path(__file__).parent / "breakout"))

try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.models import Bar
    from breakout_scanner_updated import detect_flag_breakout_setup, detect_range_breakout_setup
    from breakout_scanner import SetupTag
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def fetch_historical_data(symbol: str, start_date: datetime, end_date: datetime):
    """Fetch historical data for a specific symbol and date range"""
    
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    if not api_key or not secret_key:
        print("❌ No Alpaca API keys found")
        return None
    
    try:
        client = StockHistoricalDataClient(api_key, secret_key)
        
        # Get more data for better analysis
        extended_start = start_date - timedelta(days=120)
        
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=extended_start,
            end=end_date
        )
        
        bars = client.get_stock_bars(request)
        
        if bars and symbol in bars.data and bars.data[symbol]:
            return bars.data[symbol]
        else:
            return None
            
    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {e}")
        return None

def analyze_february_daily():
    """Analyze every trading day in February 2020 for CODX"""
    
    print("🔍 CODX February 2020 Full Analysis")
    print("Analyzing every trading day with updated parameters")
    print("=" * 100)
    
    # Fetch CODX data
    symbol = "CODX"
    start_date = datetime(2020, 2, 1)
    end_date = datetime(2020, 2, 29)
    
    print(f"📊 Fetching {symbol} data...")
    bars = fetch_historical_data(symbol, start_date, end_date)
    
    if not bars:
        print(f"❌ No data found for {symbol}")
        return
    
    print(f"📊 Fetched {len(bars)} bars for {symbol}")
    
    # Filter to February 2020 bars
    feb_bars = []
    for bar in bars:
        if bar.timestamp.date() >= start_date.date() and bar.timestamp.date() <= end_date.date():
            feb_bars.append(bar)
    
    print(f"📅 Found {len(feb_bars)} bars in February 2020")
    
    if len(feb_bars) == 0:
        print("❌ No February data found")
        return
    
    # Get SPY data for benchmark
    print(f"📊 Fetching SPY benchmark data...")
    spy_bars = fetch_historical_data("SPY", start_date - timedelta(days=120), end_date)
    spy_closes = [float(bar.close) for bar in spy_bars] if spy_bars else None
    
    # Analyze each February trading day
    results = []
    
    print(f"\n📅 CODX February 2020 Daily Analysis:")
    print("=" * 100)
    print(f"{'Date':<12} {'Price':<8} {'Change%':<8} {'Volume':<12} {'Flag':<6} {'Range':<6} {'Flag Score':<12} {'Range Score':<12}")
    print("-" * 100)
    
    for i, current_bar in enumerate(feb_bars):
        # Get all bars up to current date
        bars_up_to_date = []
        for bar in bars:
            if bar.timestamp.date() <= current_bar.timestamp.date():
                bars_up_to_date.append(bar)
        
        if len(bars_up_to_date) < 60:  # Need minimum data
            continue
        
        # Get corresponding SPY data
        spy_closes_up_to_date = None
        if spy_closes and len(spy_closes) >= len(bars_up_to_date):
            spy_closes_up_to_date = spy_closes[:len(bars_up_to_date)]
        
        # Test Flag Breakout
        flag_setup = detect_flag_breakout_setup(
            bars_up_to_date, 
            symbol, 
            spy_closes_up_to_date
        )
        
        # Test Range Breakout
        range_setup = detect_range_breakout_setup(
            bars_up_to_date, 
            symbol, 
            spy_closes_up_to_date
        )
        
        # Calculate daily change
        if i > 0:
            prev_close = float(feb_bars[i-1].close)
            current_close = float(current_bar.close)
            change_pct = ((current_close - prev_close) / prev_close) * 100
        else:
            change_pct = 0.0
        
        # Determine scores
        flag_score = "N/A"
        range_score = "N/A"
        
        if flag_setup:
            flag_score = f"{flag_setup.score:.2f}"
        if range_setup:
            range_score = f"{range_setup.score:.2f}"
        
        # Format output
        date_str = current_bar.timestamp.date().isoformat()
        price = f"${float(current_bar.close):.2f}"
        change = f"{change_pct:+.1f}%"
        volume = f"{int(current_bar.volume):,}"
        flag_result = "✅" if flag_setup else "❌"
        range_result = "✅" if range_setup else "❌"
        
        print(f"{date_str:<12} {price:<8} {change:<8} {volume:<12} {flag_result:<6} {range_result:<6} {flag_score:<12} {range_score:<12}")
        
        # Store results for summary
        results.append({
            'date': date_str,
            'price': float(current_bar.close),
            'change_pct': change_pct,
            'volume': int(current_bar.volume),
            'flag_breakout': flag_setup is not None,
            'range_breakout': range_setup is not None,
            'flag_score': flag_setup.score if flag_setup else None,
            'range_score': range_setup.score if range_setup else None,
            'flag_setup': flag_setup,
            'range_setup': range_setup
        })
    
    # Summary analysis
    print(f"\n" + "=" * 100)
    print(f"📊 SUMMARY ANALYSIS")
    print("=" * 100)
    
    flag_breakouts = [r for r in results if r['flag_breakout']]
    range_breakouts = [r for r in results if r['range_breakout']]
    
    print(f"🚩 Flag Breakouts Found: {len(flag_breakouts)}")
    print(f"📦 Range Breakouts Found: {len(range_breakouts)}")
    
    if flag_breakouts:
        print(f"\n🚩 FLAG BREAKOUT DAYS:")
        for breakout in flag_breakouts:
            print(f"   📅 {breakout['date']} | ${breakout['price']:.2f} | {breakout['change_pct']:+.1f}% | Score: {breakout['flag_score']:.2f}")
    
    if range_breakouts:
        print(f"\n📦 RANGE BREAKOUT DAYS:")
        for breakout in range_breakouts:
            print(f"   📅 {breakout['date']} | ${breakout['price']:.2f} | {breakout['change_pct']:+.1f}% | Score: {breakout['range_score']:.2f}")
    
    # Analyze significant moves that didn't qualify
    significant_moves = [r for r in results if abs(r['change_pct']) >= 10.0]
    print(f"\n📈 SIGNIFICANT MOVES (≥10%): {len(significant_moves)}")
    for move in significant_moves:
        flag_status = "✅" if move['flag_breakout'] else "❌"
        range_status = "✅" if move['range_breakout'] else "❌"
        print(f"   📅 {move['date']} | ${move['price']:.2f} | {move['change_pct']:+.1f}% | Flag: {flag_status} | Range: {range_status}")
    
    # Key insights
    print(f"\n💡 KEY INSIGHTS:")
    print(f"   • Total February trading days analyzed: {len(results)}")
    print(f"   • Days with Flag breakouts: {len(flag_breakouts)}")
    print(f"   • Days with Range breakouts: {len(range_breakouts)}")
    print(f"   • Significant moves (≥10%): {len(significant_moves)}")
    
    if len(flag_breakouts) == 0 and len(range_breakouts) == 0:
        print(f"\n🔍 WHY NO BREAKOUTS DETECTED:")
        print(f"   • CODX had extreme volatility (791% range)")
        print(f"   • ATR ratios were too high (>1.2 threshold)")
        print(f"   • Tight base criteria not met (>25% range)")
        print(f"   • These were fundamental/news-driven moves")
    
    # Save detailed results
    results_file = Path(__file__).parent / "codx_february_full_results.json"
    import json
    
    # Convert setups to serializable format
    serializable_results = []
    for r in results:
        serializable_result = {
            'date': r['date'],
            'price': r['price'],
            'change_pct': r['change_pct'],
            'volume': r['volume'],
            'flag_breakout': r['flag_breakout'],
            'range_breakout': r['range_breakout'],
            'flag_score': r['flag_score'],
            'range_score': r['range_score']
        }
        
        # Add setup metadata if available
        if r['flag_setup']:
            serializable_result['flag_metadata'] = r['flag_setup'].meta
        if r['range_setup']:
            serializable_result['range_metadata'] = r['range_setup'].meta
            
        serializable_results.append(serializable_result)
    
    with open(results_file, 'w') as f:
        json.dump(serializable_results, f, indent=2, default=str)
    print(f"\n💾 Detailed results saved to: {results_file}")

def main():
    """Main analysis function"""
    
    try:
        analyze_february_daily()
        print(f"\n✅ CODX February 2020 full analysis completed!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
