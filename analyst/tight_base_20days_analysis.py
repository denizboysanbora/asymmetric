#!/usr/bin/env python3
"""
Tight Base Analysis - 20 Trading Days vs 30 Trading Days
Shows the difference between 20-day and 30-day tight base calculations
"""
import os
import sys
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Load environment variables
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / "config" / "api_keys.env"
    if env_file.exists():
        load_dotenv(env_file)
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

def get_july_data():
    """Get all PRTS data for July 2020"""
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    client = StockHistoricalDataClient(api_key, secret_key)
    
    request = StockBarsRequest(
        symbol_or_symbols="PRTS",
        timeframe=TimeFrame.Day,
        start=datetime(2020, 1, 1),
        end=datetime(2020, 7, 31)
    )
    
    bars = client.get_stock_bars(request)
    return bars.data["PRTS"]

def analyze_tight_base_timeframes(bars: List[Bar]):
    """Compare tight base calculation using 20 vs 30 trading days"""
    
    print("📦 TIGHT BASE TIMEFRAME ANALYSIS")
    print("=" * 80)
    print("🎯 Comparing 20-day vs 30-day tight base calculations")
    print("🎯 Shows how timeframe affects consolidation measurement")
    print("=" * 80)
    
    # Target dates to analyze
    target_dates = [
        datetime(2020, 7, 1).date(),
        datetime(2020, 7, 2).date(),
        datetime(2020, 7, 6).date(),
        datetime(2020, 7, 7).date(),
        datetime(2020, 7, 8).date()
    ]
    
    print(f"\n📊 COMPARISON TABLE:")
    print("=" * 120)
    print(f"{'Date':<12} | {'20-Day Range':<12} | {'30-Day Range':<12} | {'20-Day Result':<14} | {'30-Day Result':<14} | {'Difference':<10}")
    print("=" * 120)
    
    for target_date in target_dates:
        # Get historical data up to target date (EXCLUDING target date)
        historical_bars = [b for b in bars if b.timestamp.date() < target_date]
        
        if len(historical_bars) < 30:
            continue
        
        # Calculate 20-day tight base
        last_20_bars = historical_bars[-20:]
        closes_20 = np.array([float(bar.close) for bar in last_20_bars])
        range_high_20 = float(np.max(closes_20))
        range_low_20 = float(np.min(closes_20))
        range_pct_20 = (range_high_20 - range_low_20) / range_low_20 * 100
        result_20 = "✅ PASS" if range_pct_20 <= 55 else "❌ FAIL"
        
        # Calculate 30-day tight base
        last_30_bars = historical_bars[-30:]
        closes_30 = np.array([float(bar.close) for bar in last_30_bars])
        range_high_30 = float(np.max(closes_30))
        range_low_30 = float(np.min(closes_30))
        range_pct_30 = (range_high_30 - range_low_30) / range_low_30 * 100
        result_30 = "✅ PASS" if range_pct_30 <= 55 else "❌ FAIL"
        
        # Calculate difference
        difference = range_pct_20 - range_pct_30
        
        print(f"{target_date} | {range_pct_20:>10.1f}% | {range_pct_30:>10.1f}% | {result_20:>12} | {result_30:>12} | {difference:>+8.1f}%")
    
    print("=" * 120)
    
    # Detailed analysis for July 6th (the day that passes with 30 days)
    print(f"\n📅 DETAILED ANALYSIS - JULY 6TH:")
    print("-" * 80)
    
    target_date = datetime(2020, 7, 6).date()
    historical_bars = [b for b in bars if b.timestamp.date() < target_date]
    
    # 20-day analysis
    print("🔍 20-DAY TIGHT BASE ANALYSIS:")
    last_20_bars = historical_bars[-20:]
    closes_20 = np.array([float(bar.close) for bar in last_20_bars])
    range_high_20 = float(np.max(closes_20))
    range_low_20 = float(np.min(closes_20))
    range_pct_20 = (range_high_20 - range_low_20) / range_low_20 * 100
    
    print(f"   Period: {last_20_bars[0].timestamp.date()} to {last_20_bars[-1].timestamp.date()}")
    print(f"   Range High: ${range_high_20:.2f}")
    print(f"   Range Low: ${range_low_20:.2f}")
    print(f"   Range Percentage: {range_pct_20:.1f}%")
    print(f"   Result: {'✅ PASS' if range_pct_20 <= 55 else '❌ FAIL'}")
    
    # 30-day analysis
    print(f"\n🔍 30-DAY TIGHT BASE ANALYSIS:")
    last_30_bars = historical_bars[-30:]
    closes_30 = np.array([float(bar.close) for bar in last_30_bars])
    range_high_30 = float(np.max(closes_30))
    range_low_30 = float(np.min(closes_30))
    range_pct_30 = (range_high_30 - range_low_30) / range_low_30 * 100
    
    print(f"   Period: {last_30_bars[0].timestamp.date()} to {last_30_bars[-1].timestamp.date()}")
    print(f"   Range High: ${range_high_30:.2f}")
    print(f"   Range Low: ${range_low_30:.2f}")
    print(f"   Range Percentage: {range_pct_30:.1f}%")
    print(f"   Result: {'✅ PASS' if range_pct_30 <= 55 else '❌ FAIL'}")
    
    # Show the difference
    print(f"\n📊 COMPARISON:")
    print(f"   20-day range: {range_pct_20:.1f}%")
    print(f"   30-day range: {range_pct_30:.1f}%")
    print(f"   Difference: {range_pct_20 - range_pct_30:+.1f}%")
    
    # Show actual price data
    print(f"\n📊 ACTUAL PRICE DATA:")
    print("   20-Day Period (Last 20 days):")
    print("   Date       | Close Price")
    print("   " + "-" * 25)
    for bar in last_20_bars[-10:]:  # Show last 10 for brevity
        print(f"   {bar.timestamp.date()} | ${float(bar.close):>8.2f}")
    print("   " + "-" * 25)
    print(f"   ... and {len(last_20_bars)-10} more days")
    
    print(f"\n   30-Day Period (Last 30 days):")
    print("   Date       | Close Price")
    print("   " + "-" * 25)
    for bar in last_30_bars[-10:]:  # Show last 10 for brevity
        print(f"   {bar.timestamp.date()} | ${float(bar.close):>8.2f}")
    print("   " + "-" * 25)
    print(f"   ... and {len(last_30_bars)-10} more days")
    
    # Analysis of the difference
    print(f"\n💡 ANALYSIS OF THE DIFFERENCE:")
    if range_pct_20 < range_pct_30:
        print(f"   • 20-day range is TIGHTER than 30-day range")
        print(f"   • Shorter timeframe shows better consolidation")
        print(f"   • 20-day might be more sensitive to recent price action")
    elif range_pct_20 > range_pct_30:
        print(f"   • 20-day range is WIDER than 30-day range")
        print(f"   • Longer timeframe shows better consolidation")
        print(f"   • 30-day might be more stable for trend analysis")
    else:
        print(f"   • Both timeframes show identical consolidation")
    
    # Show impact on flag breakout detection
    print(f"\n🎯 IMPACT ON FLAG BREAKOUT DETECTION:")
    print(f"   Current threshold: 55%")
    print(f"   20-day result: {'✅ Would pass' if range_pct_20 <= 55 else '❌ Would fail'}")
    print(f"   30-day result: {'✅ Would pass' if range_pct_30 <= 55 else '❌ Would fail'}")
    
    if (range_pct_20 <= 55) != (range_pct_30 <= 55):
        print(f"   ⚠️  DIFFERENT RESULTS: 20-day and 30-day would give different signals!")
    else:
        print(f"   ✅ SAME RESULT: Both timeframes agree on the signal")

def main():
    """Main analysis function"""
    print("🔍 Tight Base Timeframe Analysis")
    print("Comparing 20-day vs 30-day tight base calculations")
    
    try:
        # Get data
        bars = get_july_data()
        print(f"📊 Fetched {len(bars)} total bars")
        
        # Analyze tight base timeframes
        analyze_tight_base_timeframes(bars)
        
        print("\n" + "=" * 80)
        print("📋 SUMMARY:")
        print("=" * 80)
        print("🎯 20-day timeframe: More sensitive to recent price action")
        print("🎯 30-day timeframe: More stable, includes longer trend context")
        print("🎯 Shorter timeframe = tighter range (usually)")
        print("🎯 Longer timeframe = wider range (usually)")
        print("💡 Choice depends on whether you want recent or historical context")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
