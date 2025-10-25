#!/usr/bin/env python3
"""
Test NASDAQ 90-Day Database with Breakout Analysis
Tests the consolidated database with our updated breakout parameters
"""
import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from breakout.breakout_scanner_updated import detect_flag_breakout_setup, detect_range_breakout_setup

def load_nasdaq_data():
    """Load data from the consolidated 90-day database"""
    
    db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq.db"
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return None, None
    
    conn = sqlite3.connect(db_path)
    
    # Get list of all symbols
    symbols_query = "SELECT DISTINCT symbol FROM nasdaq_prices ORDER BY symbol"
    symbols_df = pd.read_sql_query(symbols_query, conn)
    symbols = symbols_df['symbol'].tolist()
    
    print(f"📊 Found {len(symbols)} symbols in 90-day database")
    
    # Get database info
    info_query = """
    SELECT 
        MIN(date) as start_date, 
        MAX(date) as end_date, 
        COUNT(DISTINCT date) as trading_days,
        COUNT(*) as total_records
    FROM nasdaq_prices
    """
    info_result = conn.execute(info_query).fetchone()
    
    print(f"📅 Date range: {info_result[0]} to {info_result[1]}")
    print(f"📊 Trading days: {info_result[2]}")
    print(f"📊 Total records: {info_result[3]}")
    
    # Get SPY data for market filter (if available)
    spy_query = """
    SELECT date, close, high, low, volume
    FROM nasdaq_prices 
    WHERE symbol = 'SPY' 
    ORDER BY date
    """
    spy_df = pd.read_sql_query(spy_query, conn)
    
    if spy_df.empty:
        print("⚠️  No SPY data found for market filter")
        spy_closes = None
    else:
        spy_closes = spy_df['close'].tolist()
        print(f"📈 SPY data: {len(spy_closes)} days")
    
    conn.close()
    
    return symbols, spy_df, spy_closes

def get_stock_data(symbol: str, spy_df: pd.DataFrame):
    """Get stock data for a specific symbol"""
    db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq.db"
    conn = sqlite3.connect(db_path)
    
    query = """
    SELECT date, close, high, low, volume, rsi, atr, sma_20, sma_50
    FROM nasdaq_prices 
    WHERE symbol = ? 
    ORDER BY date
    """
    
    df = pd.read_sql_query(query, conn, params=[symbol])
    conn.close()
    
    if df.empty:
        return None
    
    # Convert to Bar-like objects for compatibility
    bars = []
    for _, row in df.iterrows():
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
    """Analyze a single stock for breakouts using updated parameters"""
    
    if not bars or len(bars) < 60:
        return None
    
    # Filter by minimum price and volume
    latest_bar = bars[-1]
    if latest_bar.close < min_price or latest_bar.volume < min_volume:
        return None
    
    # Check if we have enough SPY data
    if spy_closes and len(spy_closes) == len(bars):
        benchmark_closes = spy_closes
    else:
        benchmark_closes = None
    
    # Analyze Flag Breakout with updated parameters
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
    
    # Analyze Range Breakout with updated parameters
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
    """Main test function"""
    print("🔍 Testing NASDAQ 90-Day Database with Breakout Analysis")
    print("Using updated unified parameters: 20-day base, 25% tight base, market filter")
    print("=" * 80)
    
    # Load data
    data = load_nasdaq_data()
    if not data:
        return
    
    symbols, spy_df, spy_closes = data
    
    print(f"\n📊 Analyzing {len(symbols)} symbols for breakouts...")
    print("🔧 Filters: Price ≥ $5, Volume ≥ 100K")
    print("🔧 Updated Parameters: 20-day base, 25% tight base, market filter enabled")
    print("=" * 80)
    
    breakout_results = []
    flag_breakouts = []
    range_breakouts = []
    
    # Analyze each symbol
    for i, symbol in enumerate(symbols):
        if i % 10 == 0:
            print(f"📈 Progress: {i}/{len(symbols)} symbols analyzed...")
        
        try:
            bars = get_stock_data(symbol, spy_df)
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
        print(f"{'Symbol':<8} | {'Price':<8} | {'Score':<6} | {'Range%':<8} | {'Vol Mult':<8} | {'ATR':<6}")
        print("-" * 80)
        
        # Sort by score descending
        flag_breakouts.sort(key=lambda x: x['flag_breakout']['score'], reverse=True)
        
        for result in flag_breakouts:
            fb = result['flag_breakout']
            print(f"{result['symbol']:<8} | ${result['price']:<7.2f} | {fb['score']:<6.3f} | {fb['range_pct']:<7.1f}% | {fb['volume_mult']:<7.1f}x | {fb['atr_ratio']:<6.3f}")
    
    # Display Range Breakouts
    if range_breakouts:
        print(f"\n📦 RANGE BREAKOUTS ({len(range_breakouts)}):")
        print("-" * 80)
        print(f"{'Symbol':<8} | {'Price':<8} | {'Score':<6} | {'Range%':<8} | {'Vol Mult':<8} | {'ATR':<6}")
        print("-" * 80)
        
        # Sort by score descending
        range_breakouts.sort(key=lambda x: x['range_breakout']['score'], reverse=True)
        
        for result in range_breakouts:
            rb = result['range_breakout']
            print(f"{result['symbol']:<8} | ${result['price']:<7.2f} | {rb['score']:<6.3f} | {rb['range_pct']:<7.1f}% | {rb['volume_mult']:<7.1f}x | {rb['atr_ratio']:<6.3f}")
    
    print(f"\n💾 Test completed!")
    print("\n🎯 The consolidated 90-day database is working with the updated breakout parameters!")

if __name__ == "__main__":
    main()
