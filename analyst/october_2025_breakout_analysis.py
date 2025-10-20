#!/usr/bin/env python3
"""
October 2025 Breakout Analysis
Analyzes the full NASDAQ universe for potential breakouts in October 2025
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

def load_october_data():
    """Load October 2025 data from the 90-day database"""
    
    db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq_90day.db"
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return None, None
    
    conn = sqlite3.connect(db_path)
    
    # Get list of all symbols
    symbols_query = "SELECT DISTINCT symbol FROM nasdaq_prices ORDER BY symbol"
    symbols_df = pd.read_sql_query(symbols_query, conn)
    symbols = symbols_df['symbol'].tolist()
    
    print(f"📊 Found {len(symbols)} symbols in 90-day database")
    
    # Get SPY data for market filter
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
    
    return symbols, spy_closes

def get_stock_data(symbol: str, spy_closes: Optional[List[float]] = None):
    """Get stock data for a specific symbol"""
    
    db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq_90day.db"
    conn = sqlite3.connect(db_path)
    
    query = """
    SELECT date, close, high, low, volume
    FROM nasdaq_prices 
    WHERE symbol = ? 
    ORDER BY date
    """
    
    df = pd.read_sql_query(query, conn, params=[symbol])
    conn.close()
    
    if df.empty or len(df) < 60:  # Need at least 60 days for breakout analysis
        return None, None
    
    # Convert to Bar objects (using Alpaca Bar structure)
    bars = []
    for _, row in df.iterrows():
        # Create a simple Bar-like object
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
    
    return bars, spy_closes

def analyze_october_breakouts():
    """Analyze October 2025 for potential breakouts"""
    
    print("🔍 October 2025 Breakout Analysis")
    print("Using full NASDAQ universe with updated parameters")
    print("=" * 70)
    
    # Load data
    symbols, spy_closes = load_october_data()
    if not symbols:
        return
    
    print(f"📅 Analyzing {len(symbols)} symbols for October 2025 breakouts...")
    print(f"🔧 Parameters: 20-day base, 25% tight base, market filter enabled")
    print(f"🔧 Filters: Price ≥ $5, Volume ≥ 100K")
    print("=" * 70)
    
    flag_breakouts = []
    range_breakouts = []
    analyzed_count = 0
    
    for i, symbol in enumerate(symbols):
        if i % 100 == 0:
            print(f"📈 Progress: {i}/{len(symbols)} symbols analyzed...")
        
        # Get stock data
        bars, benchmark_closes = get_stock_data(symbol, spy_closes)
        if not bars:
            continue
        
        # Apply filters
        latest_price = bars[-1].close
        latest_volume = bars[-1].volume
        
        if latest_price < 5.0 or latest_volume < 100000:
            continue
        
        analyzed_count += 1
        
        # Check for flag breakout
        flag_setup = detect_flag_breakout_setup(
            bars=bars,
            symbol=symbol,
            benchmark_closes=benchmark_closes,
            base_len=20,  # 20-day base
            max_range_width_pct=25.0,  # 25% tight base
            atr_len=14,
            atr_ma=50,
            atr_ratio_thresh=0.8,
            require_higher_lows=False,  # Optional for Flag
            min_break_above_pct=1.0,  # Relaxed threshold
            vol_ma=50,
            vol_mult=1.5,
            use_market_filter=True  # Market filter enabled
        )
        
        if flag_setup:
            flag_breakouts.append({
                'symbol': symbol,
                'price': latest_price,
                'volume': latest_volume,
                'setup': flag_setup
            })
        
        # Check for range breakout
        range_setup = detect_range_breakout_setup(
            bars=bars,
            symbol=symbol,
            benchmark_closes=benchmark_closes,
            base_len=20,  # 20-day base
            max_range_width_pct=25.0,  # 25% tight base
            atr_len=14,
            atr_ma=50,
            atr_ratio_thresh=0.80,
            require_higher_lows=True,  # Required for Range
            min_break_above_pct=1.5,  # Strict threshold
            vol_ma=50,
            vol_mult=1.5,
            use_market_filter=True
        )
        
        if range_setup:
            range_breakouts.append({
                'symbol': symbol,
                'price': latest_price,
                'volume': latest_volume,
                'setup': range_setup
            })
    
    # Display results
    print("\n" + "=" * 70)
    print("🎯 OCTOBER 2025 BREAKOUT ANALYSIS RESULTS")
    print("=" * 70)
    print(f"📊 Total symbols analyzed: {analyzed_count}")
    print(f"🚩 Flag breakouts found: {len(flag_breakouts)}")
    print(f"📦 Range breakouts found: {len(range_breakouts)}")
    print(f"🎯 Total breakout signals: {len(flag_breakouts) + len(range_breakouts)}")
    
    if flag_breakouts:
        print(f"\n🚩 FLAG BREAKOUTS ({len(flag_breakouts)}):")
        print("-" * 50)
        for breakout in flag_breakouts:
            print(f"  {breakout['symbol']:<8} ${breakout['price']:>8.2f} Vol: {breakout['volume']:>10,}")
    
    if range_breakouts:
        print(f"\n📦 RANGE BREAKOUTS ({len(range_breakouts)}):")
        print("-" * 50)
        for breakout in range_breakouts:
            print(f"  {breakout['symbol']:<8} ${breakout['price']:>8.2f} Vol: {breakout['volume']:>10,}")
    
    if not flag_breakouts and not range_breakouts:
        print(f"\n💡 No breakouts found with current parameters.")
        print(f"   Consider:")
        print(f"   - Relaxing tight base threshold (currently 25%)")
        print(f"   - Reducing price breakout threshold")
        print(f"   - Adjusting volume requirements")
    
    # Save results
    results = {
        'analysis_date': datetime.now().isoformat(),
        'total_symbols_analyzed': analyzed_count,
        'flag_breakouts': flag_breakouts,
        'range_breakouts': range_breakouts,
        'parameters': {
            'base_len': 20,
            'max_range_width_pct': 25.0,
            'atr_ratio_thresh': 0.8,
            'min_break_above_pct': {'flag': 1.0, 'range': 1.5},
            'use_market_filter': True
        }
    }
    
    results_file = Path(__file__).parent / "october_2025_breakout_results.json"
    import json
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    return flag_breakouts, range_breakouts

def main():
    """Main analysis function"""
    
    try:
        flag_breakouts, range_breakouts = analyze_october_breakouts()
        
        print("\n✅ October 2025 breakout analysis completed!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
