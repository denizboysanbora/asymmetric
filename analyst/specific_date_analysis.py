#!/usr/bin/env python3
"""
Specific Date Analysis
Check specific dates for breakout patterns
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
            print(f"📊 Fetched {len(bars.data[symbol])} bars for {symbol}")
            return bars.data[symbol]
        else:
            print(f"❌ No data found for {symbol}")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {e}")
        return None

def analyze_specific_date(bars: List[Bar], symbol: str, target_date: datetime):
    """Analyze breakout patterns for a specific date"""
    
    if not bars or len(bars) < 60:
        print(f"❌ Insufficient data for {symbol}")
        return None
    
    print(f"\n🔍 Analyzing {symbol} for {target_date.date()}...")
    
    # Find bars up to and including the target date
    bars_up_to_date = []
    target_bar = None
    
    for bar in bars:
        if bar.timestamp.date() <= target_date.date():
            bars_up_to_date.append(bar)
            if bar.timestamp.date() == target_date.date():
                target_bar = bar
    
    if not target_bar:
        print(f"❌ No data found for {target_date.date()}")
        return None
    
    if len(bars_up_to_date) < 60:
        print(f"❌ Insufficient historical data: {len(bars_up_to_date)} bars")
        return None
    
    print(f"📊 Using {len(bars_up_to_date)} bars for analysis")
    print(f"📅 Target date bar: {target_date.date()} - ${target_bar.close:.2f}")
    
    # Check flag breakout
    flag_setup = detect_flag_breakout_setup(
        bars=bars_up_to_date,
        symbol=symbol,
        benchmark_closes=None,
        base_len=20,
        max_range_width_pct=25.0,
        atr_len=14,
        atr_ma=50,
        atr_ratio_thresh=0.8,
        require_higher_lows=False,
        min_break_above_pct=1.0,
        vol_ma=50,
        vol_mult=1.5,
        use_market_filter=False
    )
    
    # Check range breakout
    range_setup = detect_range_breakout_setup(
        bars=bars_up_to_date,
        symbol=symbol,
        benchmark_closes=None,
        base_len=20,
        max_range_width_pct=25.0,
        atr_len=14,
        atr_ma=50,
        atr_ratio_thresh=0.8,
        require_higher_lows=True,
        min_break_above_pct=1.5,
        vol_ma=50,
        vol_mult=1.5,
        use_market_filter=False
    )
    
    return {
        'symbol': symbol,
        'target_date': target_date.date().isoformat(),
        'target_price': float(target_bar.close),
        'target_volume': int(target_bar.volume),
        'total_bars': len(bars_up_to_date),
        'flag_breakout': flag_setup,
        'range_breakout': range_setup
    }

def analyze_date_range(bars: List[Bar], symbol: str, start_date: datetime, end_date: datetime):
    """Analyze breakout patterns for a date range"""
    
    if not bars or len(bars) < 60:
        print(f"❌ Insufficient data for {symbol}")
        return None
    
    print(f"\n🔍 Analyzing {symbol} from {start_date.date()} to {end_date.date()}...")
    
    # Find bars in the date range
    range_bars = []
    for bar in bars:
        if start_date.date() <= bar.timestamp.date() <= end_date.date():
            range_bars.append(bar)
    
    if len(range_bars) < 5:
        print(f"❌ Insufficient data in date range: {len(range_bars)} bars")
        return None
    
    print(f"📊 Found {len(range_bars)} bars in date range")
    
    # Analyze each day in the range
    daily_results = []
    
    for bar in range_bars:
        bar_date = bar.timestamp.date()
        
        # Get bars up to this date
        bars_up_to_date = [b for b in bars if b.timestamp.date() <= bar_date]
        
        if len(bars_up_to_date) < 60:
            continue
        
        # Check flag breakout
        flag_setup = detect_flag_breakout_setup(
            bars=bars_up_to_date,
            symbol=symbol,
            benchmark_closes=None,
            base_len=20,
            max_range_width_pct=25.0,
            atr_len=14,
            atr_ma=50,
            atr_ratio_thresh=0.8,
            require_higher_lows=False,
            min_break_above_pct=1.0,
            vol_ma=50,
            vol_mult=1.5,
            use_market_filter=False
        )
        
        # Check range breakout
        range_setup = detect_range_breakout_setup(
            bars=bars_up_to_date,
            symbol=symbol,
            benchmark_closes=None,
            base_len=20,
            max_range_width_pct=25.0,
            atr_len=14,
            atr_ma=50,
            atr_ratio_thresh=0.8,
            require_higher_lows=True,
            min_break_above_pct=1.5,
            vol_ma=50,
            vol_mult=1.5,
            use_market_filter=False
        )
        
        daily_results.append({
            'date': bar_date.isoformat(),
            'price': float(bar.close),
            'volume': int(bar.volume),
            'flag_breakout': flag_setup,
            'range_breakout': range_setup
        })
    
    return {
        'symbol': symbol,
        'start_date': start_date.date().isoformat(),
        'end_date': end_date.date().isoformat(),
        'total_days': len(daily_results),
        'daily_results': daily_results
    }

def display_results(results: Dict, analysis_type: str):
    """Display analysis results"""
    
    if not results:
        return
    
    symbol = results['symbol']
    
    print(f"\n" + "=" * 80)
    print(f"🎯 {symbol} {analysis_type.upper()} ANALYSIS RESULTS")
    print("=" * 80)
    
    if analysis_type == "specific_date":
        print(f"📅 Target Date: {results['target_date']}")
        print(f"📊 Price: ${results['target_price']:.2f}")
        print(f"📊 Volume: {results['target_volume']:,}")
        print(f"📊 Total Bars: {results['total_bars']}")
        
        print(f"\n🎯 BREAKOUT ANALYSIS:")
        
        if results['flag_breakout']:
            flag = results['flag_breakout']
            print(f"   🚩 Flag Breakout: ✅ DETECTED!")
            print(f"      📊 Score: {flag.score:.3f}")
            print(f"      📊 Triggered: {flag.triggered}")
            if hasattr(flag, 'meta') and flag.meta:
                meta = flag.meta
                print(f"      📊 Prior Impulse: {meta.get('impulse_pct', 'N/A'):.1f}%")
                print(f"      📏 ATR Contraction: {meta.get('atr_contraction', 'N/A'):.3f}")
                print(f"      🚩 Higher Lows: {meta.get('higher_lows_count', 'N/A')}")
        else:
            print(f"   🚩 Flag Breakout: ❌ Not detected")
        
        if results['range_breakout']:
            range_brk = results['range_breakout']
            print(f"   📦 Range Breakout: ✅ DETECTED!")
            print(f"      📊 Score: {range_brk.score:.3f}")
            print(f"      📊 Triggered: {range_brk.triggered}")
            if hasattr(range_brk, 'meta') and range_brk.meta:
                meta = range_brk.meta
                print(f"      📏 Tight Base: {meta.get('tight_base', 'N/A')}")
                print(f"      📊 Range Pct: {meta.get('range_pct', 'N/A'):.1f}%")
                print(f"      📈 Volume Multiple: {meta.get('volume_mult', 'N/A'):.1f}x")
        else:
            print(f"   📦 Range Breakout: ❌ Not detected")
    
    elif analysis_type == "date_range":
        print(f"📅 Period: {results['start_date']} to {results['end_date']}")
        print(f"📊 Total Days: {results['total_days']}")
        
        # Count breakouts
        flag_breakouts = [r for r in results['daily_results'] if r['flag_breakout']]
        range_breakouts = [r for r in results['daily_results'] if r['range_breakout']]
        
        print(f"🚩 Flag Breakouts: {len(flag_breakouts)}")
        print(f"📦 Range Breakouts: {len(range_breakouts)}")
        
        if flag_breakouts:
            print(f"\n🚩 FLAG BREAKOUT DAYS:")
            for breakout in flag_breakouts:
                print(f"   📅 {breakout['date']} | ${breakout['price']:.2f} | Vol: {breakout['volume']:,}")
        
        if range_breakouts:
            print(f"\n📦 RANGE BREAKOUT DAYS:")
            for breakout in range_breakouts:
                print(f"   📅 {breakout['date']} | ${breakout['price']:.2f} | Vol: {breakout['volume']:,}")
        
        if not flag_breakouts and not range_breakouts:
            print(f"\n💡 No breakouts detected in this period.")

def main():
    """Main analysis function"""
    
    print("🔍 Specific Date Analysis")
    print("Checking specific dates for breakout patterns")
    print("=" * 80)
    
    # APPS July 31st analysis
    print(f"\n📊 Fetching data for APPS July 31st, 2020...")
    apps_bars = fetch_historical_data('APPS', datetime(2020, 7, 31), datetime(2020, 7, 31))
    
    if apps_bars:
        apps_results = analyze_specific_date(apps_bars, 'APPS', datetime(2020, 7, 31))
        if apps_results:
            display_results(apps_results, "specific_date")
            
            # Save results
            results_file = Path(__file__).parent / "apps_july_31_2020_results.json"
            import json
            with open(results_file, 'w') as f:
                json.dump(apps_results, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {results_file}")
    
    # CODX February 2020 analysis
    print(f"\n📊 Fetching data for CODX February 2020...")
    codx_bars = fetch_historical_data('CODX', datetime(2020, 2, 1), datetime(2020, 2, 29))
    
    if codx_bars:
        codx_results = analyze_date_range(codx_bars, 'CODX', datetime(2020, 2, 1), datetime(2020, 2, 29))
        if codx_results:
            display_results(codx_results, "date_range")
            
            # Save results
            results_file = Path(__file__).parent / "codx_february_2020_results.json"
            import json
            with open(results_file, 'w') as f:
                json.dump(codx_results, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {results_file}")
    
    print(f"\n✅ Specific date analysis completed!")

if __name__ == "__main__":
    main()
