#!/usr/bin/env python3
"""
NASDAQ Combined Breakout Analysis (Aug-Sep-Oct 2025)
Using updated unified parameters: 20-day base, 25% tight base, market filter
Combines multiple monthly databases to get sufficient historical data
"""
import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from breakout.breakout_scanner_updated import detect_flag_breakout_setup, detect_range_breakout_setup
from breakout.breakout_scanner_updated import _sma, _atr, _higher_lows_pivots

def load_combined_nasdaq_data():
    """Load combined NASDAQ data from multiple monthly databases"""
    
    # Database files to combine (in chronological order)
    db_files = [
        "nasdaq_aug_25.db",
        "nasdaq_sep_25.db", 
        "nasdaq_oct_25.db"
    ]
    
    all_data = []
    all_spy_data = []
    
    for db_file in db_files:
        db_path = Path(__file__).parent / "nasdaq_db" / db_file
        
        if not db_path.exists():
            print(f"⚠️  Database not found: {db_path}")
            continue
        
        conn = sqlite3.connect(db_path)
        
        # Get all stock data
        query = """
        SELECT symbol, date, close, high, low, volume
        FROM nasdaq_prices 
        ORDER BY symbol, date
        """
        
        df = pd.read_sql_query(query, conn)
        all_data.append(df)
        
        # Get SPY data
        spy_query = """
        SELECT date, close, high, low, volume
        FROM nasdaq_prices 
        WHERE symbol = 'SPY' 
        ORDER BY date
        """
        spy_df = pd.read_sql_query(spy_query, conn)
        if not spy_df.empty:
            all_spy_data.append(spy_df)
        
        conn.close()
        print(f"📊 Loaded {len(df)} records from {db_file}")
    
    if not all_data:
        print("❌ No data loaded from any database")
        return None
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_spy_df = pd.concat(all_spy_data, ignore_index=True) if all_spy_data else pd.DataFrame()
    
    # Remove duplicates and sort
    combined_df = combined_df.drop_duplicates(subset=['symbol', 'date']).sort_values(['symbol', 'date'])
    combined_spy_df = combined_spy_df.drop_duplicates(subset=['date']).sort_values('date') if not combined_spy_df.empty else pd.DataFrame()
    
    # Get unique symbols
    symbols = combined_df['symbol'].unique().tolist()
    
    print(f"📊 Combined data: {len(combined_df)} records for {len(symbols)} symbols")
    print(f"📅 Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
    
    if not combined_spy_df.empty:
        spy_closes = combined_spy_df['close'].tolist()
        print(f"📈 SPY data: {len(spy_closes)} days")
    else:
        spy_closes = None
        print("⚠️  No SPY data found")
    
    return symbols, combined_df, combined_spy_df, spy_closes

def get_stock_data_from_combined(symbol: str, combined_df: pd.DataFrame):
    """Get stock data for a specific symbol from combined dataframe"""
    
    symbol_data = combined_df[combined_df['symbol'] == symbol].copy()
    
    if symbol_data.empty:
        return None
    
    # Sort by date
    symbol_data = symbol_data.sort_values('date')
    
    # Convert to Bar-like objects for compatibility
    bars = []
    for _, row in symbol_data.iterrows():
        # Create a simple object that mimics Bar structure
        bar = type('Bar', (), {
            'timestamp': datetime.strptime(row['date'], '%Y-%m-%d'),
            'close': float(row['close']),
            'high': float(row['high']),
            'low': float(row['low']),
            'volume': float(row['volume']),
            'symbol': symbol
        })()
        bars.append(bar)
    
    return bars

def analyze_stock_breakouts(symbol: str, bars: List, spy_closes: List[float], min_price: float = 5.0, min_volume: int = 100000):
    """Analyze a single stock for breakouts"""
    
    if not bars or len(bars) < 40:  # Reduced minimum for combined data
        return None
    
    # Filter by minimum price and volume
    latest_bar = bars[-1]
    if latest_bar.close < min_price or latest_bar.volume < min_volume:
        return None
    
    # Check if we have enough SPY data
    if spy_closes and len(spy_closes) >= len(bars):
        benchmark_closes = spy_closes[:len(bars)]
    else:
        benchmark_closes = None
    
    # Analyze Flag Breakout
    flag_setup = detect_flag_breakout_setup(
        bars, 
        symbol, 
        benchmark_closes=benchmark_closes,
        base_len=20,  # Updated parameter
        max_range_width_pct=25.0,  # Updated parameter
        atr_ratio_thresh=0.9,  # Updated parameter
        require_higher_lows=False,  # Optional for Flag
        min_break_above_pct=1.0,  # Updated parameter
        use_market_filter=True  # Updated parameter
    )
    
    # Analyze Range Breakout
    range_setup = detect_range_breakout_setup(
        bars, 
        symbol, 
        benchmark_closes=benchmark_closes,
        base_len=20,  # Updated parameter
        max_range_width_pct=25.0,  # Updated parameter
        atr_ratio_thresh=0.8,  # Keep strict for Range
        require_higher_lows=True,  # Required for Range
        min_break_above_pct=1.5,  # Keep strict for Range
        use_market_filter=True  # Updated parameter
    )
    
    results = {
        'symbol': symbol,
        'price': latest_bar.close,
        'volume': latest_bar.volume,
        'date': latest_bar.timestamp.strftime('%Y-%m-%d'),
        'data_points': len(bars),
        'flag_breakout': None,
        'range_breakout': None
    }
    
    if flag_setup and flag_setup.triggered:
        results['flag_breakout'] = {
            'setup': flag_setup.setup,
            'score': flag_setup.score,
            'entry': flag_setup.meta.get('entry'),
            'stop': flag_setup.meta.get('stop'),
            'range_pct': flag_setup.meta.get('range_pct'),
            'volume_mult': flag_setup.meta.get('volume_mult'),
            'atr_ratio': flag_setup.meta.get('atr_ratio')
        }
    
    if range_setup and range_setup.triggered:
        results['range_breakout'] = {
            'setup': range_setup.setup,
            'score': range_setup.score,
            'entry': range_setup.meta.get('entry'),
            'stop': range_setup.meta.get('stop'),
            'range_pct': range_setup.meta.get('range_pct'),
            'volume_mult': range_setup.meta.get('volume_mult'),
            'atr_ratio': range_setup.meta.get('atr_ratio')
        }
    
    return results

def main():
    """Main analysis function"""
    print("🔍 NASDAQ Combined Breakout Analysis (Aug-Sep-Oct 2025)")
    print("Using updated unified parameters: 20-day base, 25% tight base, market filter")
    print("=" * 80)
    
    # Load combined data
    data = load_combined_nasdaq_data()
    if not data:
        return
    
    symbols, combined_df, combined_spy_df, spy_closes = data
    
    print(f"\n📊 Analyzing {len(symbols)} symbols for breakouts...")
    print("🔧 Filters: Price ≥ $5, Volume ≥ 100K, Min 40 data points")
    print("=" * 80)
    
    breakout_results = []
    flag_breakouts = []
    range_breakouts = []
    
    # Analyze each symbol
    for i, symbol in enumerate(symbols):
        if i % 100 == 0:
            print(f"📈 Progress: {i}/{len(symbols)} symbols analyzed...")
        
        try:
            bars = get_stock_data_from_combined(symbol, combined_df)
            if not bars:
                continue
            
            result = analyze_stock_breakouts(symbol, bars, spy_closes)
            if result:
                breakout_results.append(result)
                
                if result['flag_breakout']:
                    flag_breakouts.append(result)
                
                if result['range_breakout']:
                    range_breakouts.append(result)
        
        except Exception as e:
            print(f"⚠️  Error analyzing {symbol}: {e}")
            continue
    
    # Display results
    print(f"\n🎯 BREAKOUT ANALYSIS RESULTS")
    print("=" * 80)
    print(f"📊 Total symbols analyzed: {len(breakout_results)}")
    print(f"🚩 Flag breakouts found: {len(flag_breakouts)}")
    print(f"📦 Range breakouts found: {len(range_breakouts)}")
    print(f"🎯 Total breakout signals: {len(flag_breakouts) + len(range_breakouts)}")
    
    # Display Flag Breakouts
    if flag_breakouts:
        print(f"\n🚩 FLAG BREAKOUTS ({len(flag_breakouts)}):")
        print("-" * 80)
        print(f"{'Symbol':<8} | {'Price':<8} | {'Score':<6} | {'Range%':<8} | {'Vol Mult':<8} | {'ATR':<6} | {'Days':<5}")
        print("-" * 80)
        
        # Sort by score descending
        flag_breakouts.sort(key=lambda x: x['flag_breakout']['score'], reverse=True)
        
        for result in flag_breakouts:
            fb = result['flag_breakout']
            print(f"{result['symbol']:<8} | ${result['price']:<7.2f} | {fb['score']:<6.3f} | {fb['range_pct']:<7.1f}% | {fb['volume_mult']:<7.1f}x | {fb['atr_ratio']:<6.3f} | {result['data_points']:<5}")
    
    # Display Range Breakouts
    if range_breakouts:
        print(f"\n📦 RANGE BREAKOUTS ({len(range_breakouts)}):")
        print("-" * 80)
        print(f"{'Symbol':<8} | {'Price':<8} | {'Score':<6} | {'Range%':<8} | {'Vol Mult':<8} | {'ATR':<6} | {'Days':<5}")
        print("-" * 80)
        
        # Sort by score descending
        range_breakouts.sort(key=lambda x: x['range_breakout']['score'], reverse=True)
        
        for result in range_breakouts:
            rb = result['range_breakout']
            print(f"{result['symbol']:<8} | ${result['price']:<7.2f} | {rb['score']:<6.3f} | {rb['range_pct']:<7.1f}% | {rb['volume_mult']:<7.1f}x | {rb['atr_ratio']:<6.3f} | {result['data_points']:<5}")
    
    # Save results to JSON
    output_file = Path(__file__).parent / "nasdaq_combined_breakout_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            'analysis_date': datetime.now().isoformat(),
            'data_range': f"{combined_df['date'].min()} to {combined_df['date'].max()}",
            'parameters': {
                'base_len': 20,
                'max_range_width_pct': 25.0,
                'flag_atr_thresh': 0.9,
                'range_atr_thresh': 0.8,
                'flag_price_thresh': 1.0,
                'range_price_thresh': 1.5,
                'volume_mult': 1.5,
                'market_filter': True
            },
            'summary': {
                'total_symbols': len(breakout_results),
                'flag_breakouts': len(flag_breakouts),
                'range_breakouts': len(range_breakouts),
                'total_signals': len(flag_breakouts) + len(range_breakouts)
            },
            'flag_breakouts': flag_breakouts,
            'range_breakouts': range_breakouts
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    print("\n🎯 Analysis complete!")

if __name__ == "__main__":
    main()
