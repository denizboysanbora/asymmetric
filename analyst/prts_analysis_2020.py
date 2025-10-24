#!/usr/bin/env python3
"""
PRTS Stock Analysis for May-July 2020
Analyze breakout signals using the analyst algorithm
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import json

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

try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.models import Bar
except ImportError as e:
    print(f"Error importing Alpaca modules: {e}")
    sys.exit(1)

# Import breakout analysis functions
sys.path.insert(0, str(Path(__file__).parent))
from breakout.breakout_scanner import (
    detect_flag_breakout_setup, 
    detect_range_breakout_setup,
    calculate_rsi,
    calculate_atr,
    calculate_z_score,
    breakout_checklist
)

def fetch_prts_data(start_date: datetime, end_date: datetime) -> Optional[List[Bar]]:
    """Fetch PRTS stock data for the specified date range"""
    try:
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        if not api_key or not secret_key:
            print("❌ ALPACA_API_KEY and ALPACA_SECRET_KEY not set")
            return None
        
        client = StockHistoricalDataClient(api_key, secret_key)
        
        request = StockBarsRequest(
            symbol_or_symbols="PRTS",
            timeframe=TimeFrame.Day,
            start=start_date,
            end=end_date
        )
        
        bars = client.get_stock_bars(request)
        
        if not bars or "PRTS" not in bars.data:
            print("❌ No PRTS data found for the specified date range")
            return None
        
        prts_bars = bars.data["PRTS"]
        print(f"📊 Fetched {len(prts_bars)} PRTS bars from {start_date.date()} to {end_date.date()}")
        
        return prts_bars
        
    except Exception as e:
        print(f"❌ Error fetching PRTS data: {e}")
        return None

def fetch_spy_data(start_date: datetime, end_date: datetime) -> Optional[List[Bar]]:
    """Fetch SPY data for benchmark comparison"""
    try:
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        client = StockHistoricalDataClient(api_key, secret_key)
        
        request = StockBarsRequest(
            symbol_or_symbols="SPY",
            timeframe=TimeFrame.Day,
            start=start_date,
            end=end_date
        )
        
        bars = client.get_stock_bars(request)
        
        if not bars or "SPY" not in bars.data:
            return None
        
        return bars.data["SPY"]
        
    except Exception as e:
        print(f"❌ Error fetching SPY data: {e}")
        return None

def analyze_breakout_signals(bars: List[Bar], spy_bars: List[Bar]) -> Dict:
    """Analyze PRTS data for breakout signals"""
    if len(bars) < 60:
        return {"error": "Insufficient data for analysis"}
    
    results = {
        "symbol": "PRTS",
        "total_days": len(bars),
        "date_range": f"{bars[0].timestamp.date()} to {bars[-1].timestamp.date()}",
        "flag_breakouts": [],
        "range_breakouts": [],
        "daily_analysis": []
    }
    
    # Analyze each day for potential breakouts
    for i in range(60, len(bars)):  # Need at least 60 days of history
        current_date = bars[i].timestamp.date()
        current_bars = bars[:i+1]  # All bars up to current date
        
        # Check for flag breakout
        flag_breakout = detect_flag_breakout_setup(current_bars, "PRTS")
        
        # Check for range breakout
        range_breakout = detect_range_breakout_setup(current_bars, "PRTS")
        
        # Calculate technical indicators
        closes = [float(bar.close) for bar in current_bars]
        highs = [float(bar.high) for bar in current_bars]
        lows = [float(bar.low) for bar in current_bars]
        
        rsi = calculate_rsi(closes)
        atr = calculate_atr(highs, lows, closes)
        z_score = calculate_z_score(closes)
        
        daily_info = {
            "date": current_date,
            "price": closes[-1],
            "rsi": rsi,
            "atr": atr,
            "z_score": z_score,
            "flag_breakout": flag_breakout is not None,
            "range_breakout": range_breakout is not None
        }
        
        if flag_breakout:
            daily_info["flag_breakout_details"] = {
                "score": flag_breakout.score,
                "triggered": flag_breakout.triggered,
                "meta": flag_breakout.meta
            }
            results["flag_breakouts"].append({
                "date": current_date,
                "price": closes[-1],
                "score": flag_breakout.score,
                "details": flag_breakout.meta
            })
        
        if range_breakout:
            daily_info["range_breakout_details"] = {
                "score": range_breakout.score,
                "triggered": range_breakout.triggered,
                "meta": range_breakout.meta
            }
            results["range_breakouts"].append({
                "date": current_date,
                "price": closes[-1],
                "score": range_breakout.score,
                "details": range_breakout.meta
            })
        
        results["daily_analysis"].append(daily_info)
    
    return results

def print_analysis_summary(results: Dict):
    """Print a summary of the analysis"""
    print("\n" + "="*60)
    print("📊 PRTS BREAKOUT ANALYSIS SUMMARY (May-July 2020)")
    print("="*60)
    
    print(f"📈 Symbol: {results['symbol']}")
    print(f"📅 Date Range: {results['date_range']}")
    print(f"📊 Total Trading Days: {results['total_days']}")
    
    print(f"\n🚩 FLAG BREAKOUTS DETECTED: {len(results['flag_breakouts'])}")
    if results['flag_breakouts']:
        for breakout in results['flag_breakouts']:
            print(f"  • {breakout['date']}: ${breakout['price']:.2f} (Score: {breakout['score']:.3f})")
            if 'impulse_pct' in breakout['details']:
                print(f"    - Impulse: {breakout['details']['impulse_pct']:.1f}%")
            if 'atr_contraction' in breakout['details']:
                print(f"    - ATR Contraction: {breakout['details']['atr_contraction']:.3f}")
    else:
        print("  No flag breakouts detected")
    
    print(f"\n📦 RANGE BREAKOUTS DETECTED: {len(results['range_breakouts'])}")
    if results['range_breakouts']:
        for breakout in results['range_breakouts']:
            print(f"  • {breakout['date']}: ${breakout['price']:.2f} (Score: {breakout['score']:.3f})")
            if 'range_pct' in breakout['details']:
                print(f"    - Range Width: {breakout['details']['range_pct']:.1f}%")
            if 'volume_mult' in breakout['details']:
                print(f"    - Volume Multiple: {breakout['details']['volume_mult']:.1f}x")
    else:
        print("  No range breakouts detected")
    
    # Show daily checklist for key dates
    print(f"\n📋 DAILY BREAKOUT CHECKLIST (Key Dates):")
    print("-" * 60)
    
    # Show first few days and any breakout days
    key_dates = []
    for i, daily in enumerate(results['daily_analysis'][:5]):  # First 5 days
        key_dates.append(daily)
    
    # Add breakout days
    for daily in results['daily_analysis']:
        if daily['flag_breakout'] or daily['range_breakout']:
            key_dates.append(daily)
    
    # Remove duplicates and sort by date
    seen_dates = set()
    unique_dates = []
    for daily in key_dates:
        if daily['date'] not in seen_dates:
            unique_dates.append(daily)
            seen_dates.add(daily['date'])
    
    unique_dates.sort(key=lambda x: x['date'])
    
    for daily in unique_dates:
        breakout_type = ""
        if daily['flag_breakout'] and daily['range_breakout']:
            breakout_type = " (FLAG + RANGE)"
        elif daily['flag_breakout']:
            breakout_type = " (FLAG)"
        elif daily['range_breakout']:
            breakout_type = " (RANGE)"
        
        print(f"📅 {daily['date']}: ${daily['price']:.2f} | "
              f"RSI: {daily['rsi']:.0f} | "
              f"ATR: {daily['atr']:.2f} | "
              f"Z-Score: {daily['z_score']:.2f}{breakout_type}")

def main():
    """Main analysis function"""
    print("🔍 PRTS Stock Analysis - May-July 2020")
    print("Analyzing breakout signals using the analyst algorithm")
    
    # Define date range for May-July 2020
    start_date = datetime(2020, 5, 1)
    end_date = datetime(2020, 7, 31)
    
    print(f"📅 Analyzing period: {start_date.date()} to {end_date.date()}")
    
    # Fetch PRTS data
    print("\n📊 Fetching PRTS stock data...")
    prts_bars = fetch_prts_data(start_date, end_date)
    
    if not prts_bars:
        print("❌ Failed to fetch PRTS data")
        return
    
    # Fetch SPY data for benchmark
    print("📊 Fetching SPY benchmark data...")
    spy_bars = fetch_spy_data(start_date, end_date)
    
    if not spy_bars:
        print("⚠️  Warning: Could not fetch SPY data, analysis will be limited")
    
    # Analyze breakout signals
    print("\n🔍 Analyzing breakout signals...")
    results = analyze_breakout_signals(prts_bars, spy_bars)
    
    # Print summary
    print_analysis_summary(results)
    
    # Save detailed results to file
    output_file = Path(__file__).parent / "prts_analysis_results_2020.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    # Show breakout checklist for the last few days
    if spy_bars and len(spy_bars) > 0:
        print(f"\n📋 BREAKOUT CHECKLIST (Last 5 Days):")
        print("-" * 60)
        
        # Get the last 5 days of analysis
        last_5_days = results['daily_analysis'][-5:]
        for daily in last_5_days:
            # Find the corresponding bars for this date
            date_bars = [bar for bar in prts_bars if bar.timestamp.date() <= daily['date']]
            if len(date_bars) >= 60:  # Need enough history
                try:
                    checklist = breakout_checklist("PRTS", date_bars, spy_bars)
                    print(checklist)
                except Exception as e:
                    print(f"Error generating checklist for {daily['date']}: {e}")

if __name__ == "__main__":
    main()
