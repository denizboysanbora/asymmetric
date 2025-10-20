#!/usr/bin/env python3
"""
Detailed Date Check
Check what data we have and analyze more thoroughly
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

try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.models import Bar
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def fetch_and_examine_data(symbol: str, start_date: datetime, end_date: datetime):
    """Fetch data and examine what we have"""
    
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
            print(f"📊 Fetched {len(bars.data[symbol])} bars for {symbol}")
            
            # Show date range
            dates = [bar.timestamp.date() for bar in bars.data[symbol]]
            print(f"📅 Date range: {min(dates)} to {max(dates)}")
            
            # Show last 10 days
            print(f"\n📅 Last 10 trading days:")
            for bar in bars.data[symbol][-10:]:
                print(f"   {bar.timestamp.date()} | ${bar.close:.2f} | Vol: {bar.volume:,}")
            
            return bars.data[symbol]
        else:
            print(f"❌ No data found for {symbol}")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {e}")
        return None

def analyze_codx_detailed(bars: List[Bar]):
    """Detailed analysis of CODX February 2020"""
    
    if not bars or len(bars) < 60:
        return None
    
    print(f"\n🔍 Detailed CODX February 2020 Analysis...")
    
    # Find February 2020 bars
    feb_bars = []
    for bar in bars:
        if bar.timestamp.month == 2 and bar.timestamp.year == 2020:
            feb_bars.append(bar)
    
    print(f"📊 Found {len(feb_bars)} bars in February 2020")
    
    if len(feb_bars) < 5:
        print(f"❌ Insufficient February data")
        return None
    
    # Show daily breakdown
    print(f"\n📅 CODX February 2020 Daily Breakdown:")
    print("-" * 80)
    print(f"{'Date':<12} {'Open':<8} {'High':<8} {'Low':<8} {'Close':<8} {'Volume':<12} {'Change':<8}")
    print("-" * 80)
    
    prev_close = None
    for bar in feb_bars:
        if prev_close is not None:
            change = ((bar.close - prev_close) / prev_close) * 100
        else:
            change = 0.0
        
        print(f"{bar.timestamp.date():<12} ${bar.open:<7.2f} ${bar.high:<7.2f} ${bar.low:<7.2f} ${bar.close:<7.2f} {bar.volume:<12,} {change:+.2f}%")
        prev_close = bar.close
    
    # Calculate key metrics
    start_price = feb_bars[0].close
    end_price = feb_bars[-1].close
    total_return = ((end_price - start_price) / start_price) * 100
    
    highs = [bar.high for bar in feb_bars]
    lows = [bar.low for bar in feb_bars]
    max_high = max(highs)
    min_low = min(lows)
    range_pct = ((max_high - min_low) / min_low) * 100
    
    volumes = [bar.volume for bar in feb_bars]
    avg_volume = np.mean(volumes)
    max_volume = max(volumes)
    volume_spike = max_volume / avg_volume
    
    print(f"\n📊 KEY METRICS:")
    print(f"   📈 Start Price: ${start_price:.2f}")
    print(f"   📈 End Price: ${end_price:.2f}")
    print(f"   📊 Total Return: {total_return:+.2f}%")
    print(f"   📏 Price Range: ${min_low:.2f} - ${max_high:.2f}")
    print(f"   📏 Range Size: {range_pct:.1f}%")
    print(f"   📊 Average Volume: {avg_volume:,.0f}")
    print(f"   📊 Max Volume: {max_volume:,}")
    print(f"   📊 Volume Spike: {volume_spike:.1f}x")
    
    # Check for specific breakout days
    print(f"\n🎯 BREAKOUT ANALYSIS:")
    
    # Look for days with significant moves
    significant_moves = []
    for i, bar in enumerate(feb_bars):
        if i > 0:
            prev_close = feb_bars[i-1].close
            change = ((bar.close - prev_close) / prev_close) * 100
            
            if abs(change) > 10:  # 10%+ moves
                significant_moves.append({
                    'date': bar.timestamp.date(),
                    'change': change,
                    'price': bar.close,
                    'volume': bar.volume
                })
    
    if significant_moves:
        print(f"   📊 Significant Moves (>10%):")
        for move in significant_moves:
            print(f"      📅 {move['date']} | {move['change']:+.1f}% | ${move['price']:.2f} | Vol: {move['volume']:,}")
    else:
        print(f"   📊 No significant single-day moves (>10%)")
    
    return {
        'feb_bars': feb_bars,
        'total_return': total_return,
        'range_pct': range_pct,
        'volume_spike': volume_spike,
        'significant_moves': significant_moves
    }

def check_apps_july_data(bars: List[Bar]):
    """Check APPS July data in detail"""
    
    if not bars or len(bars) < 30:
        return None
    
    print(f"\n🔍 Detailed APPS July 2020 Analysis...")
    
    # Find July 2020 bars
    july_bars = []
    for bar in bars:
        if bar.timestamp.month == 7 and bar.timestamp.year == 2020:
            july_bars.append(bar)
    
    print(f"📊 Found {len(july_bars)} bars in July 2020")
    
    if len(july_bars) < 5:
        print(f"❌ Insufficient July data")
        return None
    
    # Show daily breakdown
    print(f"\n📅 APPS July 2020 Daily Breakdown:")
    print("-" * 80)
    print(f"{'Date':<12} {'Open':<8} {'High':<8} {'Low':<8} {'Close':<8} {'Volume':<12} {'Change':<8}")
    print("-" * 80)
    
    prev_close = None
    for bar in july_bars:
        if prev_close is not None:
            change = ((bar.close - prev_close) / prev_close) * 100
        else:
            change = 0.0
        
        print(f"{bar.timestamp.date():<12} ${bar.open:<7.2f} ${bar.high:<7.2f} ${bar.low:<7.2f} ${bar.close:<7.2f} {bar.volume:<12,} {change:+.2f}%")
        prev_close = bar.close
    
    # Check for July 31st specifically
    july_31_bar = None
    for bar in july_bars:
        if bar.timestamp.date() == datetime(2020, 7, 31).date():
            july_31_bar = bar
            break
    
    if july_31_bar:
        print(f"\n🎯 JULY 31ST SPECIFIC:")
        print(f"   📅 Date: {july_31_bar.timestamp.date()}")
        print(f"   📊 Price: ${july_31_bar.close:.2f}")
        print(f"   📊 Volume: {july_31_bar.volume:,}")
        print(f"   📊 Range: ${july_31_bar.low:.2f} - ${july_31_bar.high:.2f}")
    else:
        print(f"\n❌ No data found for July 31st, 2020")
        print(f"   📅 Last July date: {july_bars[-1].timestamp.date()}")
    
    return {
        'july_bars': july_bars,
        'july_31_bar': july_31_bar
    }

def main():
    """Main analysis function"""
    
    print("🔍 Detailed Date Check")
    print("Examining data availability and detailed analysis")
    print("=" * 80)
    
    # Check APPS July data
    print(f"\n📊 Fetching APPS data...")
    apps_bars = fetch_and_examine_data('APPS', datetime(2020, 7, 1), datetime(2020, 8, 1))
    
    if apps_bars:
        apps_results = check_apps_july_data(apps_bars)
        if apps_results:
            # Save results
            results_file = Path(__file__).parent / "apps_july_detailed_results.json"
            import json
            with open(results_file, 'w') as f:
                json.dump(apps_results, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {results_file}")
    
    # Check CODX February data
    print(f"\n📊 Fetching CODX data...")
    codx_bars = fetch_and_examine_data('CODX', datetime(2020, 2, 1), datetime(2020, 3, 1))
    
    if codx_bars:
        codx_results = analyze_codx_detailed(codx_bars)
        if codx_results:
            # Save results
            results_file = Path(__file__).parent / "codx_february_detailed_results.json"
            import json
            with open(results_file, 'w') as f:
                json.dump(codx_results, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {results_file}")
    
    print(f"\n✅ Detailed date check completed!")

if __name__ == "__main__":
    main()
