#!/usr/bin/env python3
"""
Historical Breakout Analysis
Analyzes specific stocks in specific time periods for breakout patterns
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
        
        # Extend the date range to get enough data for technical analysis
        extended_start = start_date - timedelta(days=90)  # Get extra data for indicators
        
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

def analyze_breakout_period(symbol: str, bars: List[Bar], analysis_start: datetime, analysis_end: datetime):
    """Analyze breakout patterns for a specific period"""
    
    if not bars or len(bars) < 60:
        print(f"❌ Insufficient data for {symbol}")
        return None
    
    print(f"\n🔍 Analyzing {symbol} breakout patterns...")
    print(f"📅 Analysis period: {analysis_start.date()} to {analysis_end.date()}")
    
    # Filter bars to analysis period
    analysis_bars = []
    for bar in bars:
        bar_date = bar.timestamp.date()
        if analysis_start.date() <= bar_date <= analysis_end.date():
            analysis_bars.append(bar)
    
    if len(analysis_bars) < 20:
        print(f"❌ Insufficient data in analysis period for {symbol}")
        return None
    
    print(f"📊 Analysis bars: {len(analysis_bars)} days")
    
    # Use all bars for technical analysis (need 60+ days for indicators)
    full_bars = bars
    
    results = {
        'symbol': symbol,
        'analysis_period': f"{analysis_start.date()} to {analysis_end.date()}",
        'analysis_days': len(analysis_bars),
        'total_data_days': len(full_bars),
        'flag_breakouts': [],
        'range_breakouts': []
    }
    
    # Analyze each day in the analysis period for breakouts
    for i, bar in enumerate(analysis_bars):
        # Get bars up to this point for analysis
        bar_date = bar.timestamp.date()
        bars_up_to_date = [b for b in full_bars if b.timestamp.date() <= bar_date]
        
        if len(bars_up_to_date) < 60:  # Need enough data for analysis
            continue
        
        # Check for flag breakout
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
        
        if flag_setup:
            results['flag_breakouts'].append({
                'date': bar_date.isoformat(),
                'price': float(bar.close),
                'volume': int(bar.volume),
                'score': flag_setup.score,
                'meta': flag_setup.meta
            })
        
        # Check for range breakout
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
        
        if range_setup:
            results['range_breakouts'].append({
                'date': bar_date.isoformat(),
                'price': float(bar.close),
                'volume': int(bar.volume),
                'score': range_setup.score,
                'meta': range_setup.meta
            })
    
    return results

def display_results(results: Dict):
    """Display analysis results"""
    
    if not results:
        return
    
    symbol = results['symbol']
    period = results['analysis_period']
    
    print(f"\n" + "=" * 80)
    print(f"🎯 {symbol} BREAKOUT ANALYSIS RESULTS")
    print(f"📅 Period: {period}")
    print("=" * 80)
    
    print(f"📊 Analysis days: {results['analysis_days']}")
    print(f"📊 Total data days: {results['total_data_days']}")
    print(f"🚩 Flag breakouts: {len(results['flag_breakouts'])}")
    print(f"📦 Range breakouts: {len(results['range_breakouts'])}")
    print(f"🎯 Total breakouts: {len(results['flag_breakouts']) + len(results['range_breakouts'])}")
    
    if results['flag_breakouts']:
        print(f"\n🚩 FLAG BREAKOUTS ({len(results['flag_breakouts'])}):")
        print("-" * 80)
        for breakout in results['flag_breakouts']:
            print(f"  📅 {breakout['date']} | ${breakout['price']:>8.2f} | Vol: {breakout['volume']:>10,} | Score: {breakout['score']:.3f}")
    
    if results['range_breakouts']:
        print(f"\n📦 RANGE BREAKOUTS ({len(results['range_breakouts'])}):")
        print("-" * 80)
        for breakout in results['range_breakouts']:
            print(f"  📅 {breakout['date']} | ${breakout['price']:>8.2f} | Vol: {breakout['volume']:>10,} | Score: {breakout['score']:.3f}")
    
    if not results['flag_breakouts'] and not results['range_breakouts']:
        print(f"\n💡 No breakouts found for {symbol} in this period.")
        print(f"   This could indicate:")
        print(f"   - Consolidation phase")
        print(f"   - Insufficient momentum")
        print(f"   - Parameters too strict for this timeframe")

def main():
    """Main analysis function"""
    
    print("🔍 Historical Breakout Analysis")
    print("Analyzing specific stocks in specific time periods")
    print("=" * 80)
    
    # Define analysis targets
    analyses = [
        {
            'symbol': 'APPS',
            'start_date': datetime(2020, 7, 1),
            'end_date': datetime(2020, 7, 31),
            'description': 'APPS in July 2020'
        },
        {
            'symbol': 'CODX',
            'start_date': datetime(2020, 2, 1),
            'end_date': datetime(2020, 2, 29),
            'description': 'CODX in February 2020'
        }
    ]
    
    all_results = []
    
    for analysis in analyses:
        symbol = analysis['symbol']
        start_date = analysis['start_date']
        end_date = analysis['end_date']
        description = analysis['description']
        
        print(f"\n📊 Fetching data for {description}...")
        
        # Fetch historical data
        bars = fetch_historical_data(symbol, start_date, end_date)
        
        if not bars:
            print(f"❌ Failed to fetch data for {symbol}")
            continue
        
        # Analyze breakout patterns
        results = analyze_breakout_period(symbol, bars, start_date, end_date)
        
        if results:
            display_results(results)
            all_results.append(results)
            
            # Save individual results
            results_file = Path(__file__).parent / f"{symbol.lower()}_{start_date.year}_{start_date.month:02d}_breakout_results.json"
            import json
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {results_file}")
    
    # Save combined results
    if all_results:
        combined_file = Path(__file__).parent / "historical_breakout_analysis_results.json"
        import json
        with open(combined_file, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        print(f"\n💾 Combined results saved to: {combined_file}")
    
    print(f"\n✅ Historical breakout analysis completed!")

if __name__ == "__main__":
    main()
