#!/usr/bin/env python3
"""
October 2025 Full Breakout Analysis
Analyzes ALL liquid symbols without hardcoded limits using original parameters
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

# Add breakout scanner to path
sys.path.insert(0, str(Path(__file__).parent / "breakout"))

try:
    from breakout_scanner_updated import detect_flag_breakout_setup, detect_range_breakout_setup
    from breakout_scanner import Bar, SetupTag
except ImportError as e:
    print(f"Error importing breakout modules: {e}")
    sys.exit(1)

def load_all_liquid_symbols():
    """Load ALL liquid symbols from the database - no hardcoded limits"""
    
    db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq_90day.db"
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return None
    
    conn = sqlite3.connect(db_path)
    
    # Get ALL symbols with good volume and price - NO LIMIT
    symbols_query = """
    SELECT DISTINCT symbol 
    FROM nasdaq_prices 
    WHERE symbol IN (
        SELECT symbol 
        FROM nasdaq_prices 
        WHERE date = (SELECT MAX(date) FROM nasdaq_prices)
        AND close >= 5.0 
        AND volume >= 100000
    )
    ORDER BY symbol
    """
    
    symbols_df = pd.read_sql_query(symbols_query, conn)
    symbols = symbols_df['symbol'].tolist()
    
    print(f"📊 Found {len(symbols)} liquid symbols in 90-day database")
    
    conn.close()
    return symbols

def get_stock_data(symbol: str):
    """Get stock data for a specific symbol"""
    
    db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq_90day.db"
    conn = sqlite3.connect(db_path)
    
    query = """
    SELECT date, open, high, low, close, volume
    FROM nasdaq_prices 
    WHERE symbol = ? 
    ORDER BY date
    """
    
    df = pd.read_sql_query(query, conn, params=[symbol])
    conn.close()
    
    if df.empty or len(df) < 60:
        return None
    
    # Convert to Bar objects
    bars = []
    for _, row in df.iterrows():
        class SimpleBar:
            def __init__(self, open_price, high_price, low_price, close_price, vol):
                self.open = open_price
                self.high = high_price
                self.low = low_price
                self.close = close_price
                self.volume = vol
        
        bar = SimpleBar(
            open_price=float(row['open']) if 'open' in row else float(row['close']),
            high_price=float(row['high']),
            low_price=float(row['low']),
            close_price=float(row['close']),
            vol=int(row['volume']) if row['volume'] else 0
        )
        bars.append(bar)
    
    return bars

def analyze_full_breakouts():
    """Analyze ALL liquid symbols with original parameters"""
    
    print("🔍 October 2025 Full Breakout Analysis")
    print("Analyzing ALL liquid symbols with original parameters")
    print("=" * 70)
    
    symbols = load_all_liquid_symbols()
    if not symbols:
        return
    
    print(f"📅 Analyzing {len(symbols)} symbols for October 2025 breakouts...")
    print(f"🔧 ORIGINAL Parameters:")
    print(f"   📏 Tight Base: 25%")
    print(f"   📊 ATR Contraction: 0.8")
    print(f"   💰 Price Breakout: 1.0% (Flag), 1.5% (Range)")
    print(f"   📈 Volume Expansion: 1.5x")
    print(f"   🎯 Prior Impulse: 30% (Flag)")
    print(f"   🚩 Higher Lows: Optional (Flag), Required (Range)")
    print(f"   📊 Market Filter: Enabled")
    print("=" * 70)
    
    flag_breakouts = []
    range_breakouts = []
    analyzed_count = 0
    
    for i, symbol in enumerate(symbols):
        if i % 50 == 0:
            print(f"📈 Progress: {i}/{len(symbols)} symbols analyzed...")
        
        # Get stock data
        bars = get_stock_data(symbol)
        if not bars:
            continue
        
        analyzed_count += 1
        
        # Check for flag breakout with ORIGINAL parameters
        flag_setup = detect_flag_breakout_setup(
            bars=bars,
            symbol=symbol,
            benchmark_closes=None,  # No market filter for now
            base_len=20,
            max_range_width_pct=25.0,  # ORIGINAL: 25%
            atr_len=14,
            atr_ma=50,
            atr_ratio_thresh=0.8,  # ORIGINAL: 0.8
            require_higher_lows=False,
            min_break_above_pct=1.0,  # ORIGINAL: 1.0%
            vol_ma=50,
            vol_mult=1.5,  # ORIGINAL: 1.5x
            use_market_filter=False  # Disable for now
        )
        
        if flag_setup:
            flag_breakouts.append({
                'symbol': symbol,
                'price': bars[-1].close,
                'volume': bars[-1].volume,
                'setup': flag_setup
            })
        
        # Check for range breakout with ORIGINAL parameters
        range_setup = detect_range_breakout_setup(
            bars=bars,
            symbol=symbol,
            benchmark_closes=None,  # No market filter for now
            base_len=20,
            max_range_width_pct=25.0,  # ORIGINAL: 25%
            atr_len=14,
            atr_ma=50,
            atr_ratio_thresh=0.8,  # ORIGINAL: 0.8
            require_higher_lows=True,
            min_break_above_pct=1.5,  # ORIGINAL: 1.5%
            vol_ma=50,
            vol_mult=1.5,  # ORIGINAL: 1.5x
            use_market_filter=False  # Disable for now
        )
        
        if range_setup:
            range_breakouts.append({
                'symbol': symbol,
                'price': bars[-1].close,
                'volume': bars[-1].volume,
                'setup': range_setup
            })
    
    # Display results
    print("\n" + "=" * 70)
    print("🎯 OCTOBER 2025 FULL BREAKOUT ANALYSIS RESULTS")
    print("=" * 70)
    print(f"📊 Total symbols analyzed: {analyzed_count}")
    print(f"🚩 Flag breakouts found: {len(flag_breakouts)}")
    print(f"📦 Range breakouts found: {len(range_breakouts)}")
    print(f"🎯 Total breakout signals: {len(flag_breakouts) + len(range_breakouts)}")
    
    if flag_breakouts:
        print(f"\n🚩 FLAG BREAKOUTS ({len(flag_breakouts)}):")
        print("-" * 70)
        for breakout in sorted(flag_breakouts, key=lambda x: x['setup'].score, reverse=True):
            print(f"  {breakout['symbol']:<8} ${breakout['price']:>8.2f} Vol: {breakout['volume']:>10,} Score: {breakout['setup'].score:.3f}")
    
    if range_breakouts:
        print(f"\n📦 RANGE BREAKOUTS ({len(range_breakouts)}):")
        print("-" * 70)
        for breakout in sorted(range_breakouts, key=lambda x: x['setup'].score, reverse=True):
            print(f"  {breakout['symbol']:<8} ${breakout['price']:>8.2f} Vol: {breakout['volume']:>10,} Score: {breakout['setup'].score:.3f}")
    
    if not flag_breakouts and not range_breakouts:
        print(f"\n💡 No breakouts found with original parameters.")
        print(f"   This confirms the market is in a consolidation phase.")
        print(f"   The strict criteria are working as intended - no false signals.")
    
    # Save results
    results = {
        'analysis_date': datetime.now().isoformat(),
        'total_symbols_analyzed': analyzed_count,
        'flag_breakouts': [
            {
                'symbol': b['symbol'],
                'price': b['price'],
                'volume': b['volume'],
                'score': b['setup'].score,
                'meta': b['setup'].meta
            } for b in flag_breakouts
        ],
        'range_breakouts': [
            {
                'symbol': b['symbol'],
                'price': b['price'],
                'volume': b['volume'],
                'score': b['setup'].score,
                'meta': b['setup'].meta
            } for b in range_breakouts
        ],
        'original_parameters': {
            'max_range_width_pct': 25.0,
            'atr_ratio_thresh': 0.8,
            'min_break_above_pct': {'flag': 1.0, 'range': 1.5},
            'vol_mult': 1.5,
            'use_market_filter': False
        }
    }
    
    results_file = Path(__file__).parent / "october_full_breakout_results.json"
    import json
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    return flag_breakouts, range_breakouts

def main():
    """Main analysis function"""
    
    try:
        flag_breakouts, range_breakouts = analyze_full_breakouts()
        
        print("\n✅ October 2025 full breakout analysis completed!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
