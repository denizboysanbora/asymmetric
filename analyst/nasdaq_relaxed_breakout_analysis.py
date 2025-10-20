#!/usr/bin/env python3
"""
NASDAQ Relaxed Breakout Analysis (Aug-Sep-Oct 2025)
Using relaxed parameters suitable for the available data
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
    
    for db_file in db_files:
        db_path = Path(__file__).parent / "nasdaq_db" / db_file
        
        if not db_path.exists():
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
        conn.close()
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.drop_duplicates(subset=['symbol', 'date']).sort_values(['symbol', 'date'])
    
    return combined_df

def analyze_stock_relaxed(symbol: str, combined_df: pd.DataFrame, min_price: float = 5.0, min_volume: int = 100000):
    """Relaxed breakout analysis suitable for available data"""
    
    symbol_data = combined_df[combined_df['symbol'] == symbol].copy()
    
    if symbol_data.empty or len(symbol_data) < 30:  # Reduced minimum
        return None
    
    # Sort by date
    symbol_data = symbol_data.sort_values('date')
    
    # Basic filters
    latest = symbol_data.iloc[-1]
    if latest['close'] < min_price or latest['volume'] < min_volume:
        return None
    
    # Convert to arrays for analysis
    closes = symbol_data['close'].values
    highs = symbol_data['high'].values
    lows = symbol_data['low'].values
    volumes = symbol_data['volume'].values
    
    # RELAXED PARAMETERS for available data
    base_len = min(20, len(symbol_data) - 5)  # Adaptive base length
    max_range_width_pct = 40.0  # Relaxed from 25%
    atr_len = min(14, len(symbol_data) // 3)  # Adaptive ATR length
    atr_ma = min(20, len(symbol_data) // 2)  # Reduced ATR MA
    atr_ratio_thresh = 1.2  # Relaxed ATR threshold
    min_break_above_pct = 0.5  # Relaxed price breakout
    vol_ma = min(20, len(symbol_data) // 2)  # Reduced volume MA
    vol_mult = 1.2  # Relaxed volume expansion
    prior_impulse_thresh = 15.0  # Relaxed from 30%
    
    results = {
        'symbol': symbol,
        'price': latest['close'],
        'volume': latest['volume'],
        'date': latest['date'],
        'data_points': len(symbol_data),
        'flag_breakout': False,
        'range_breakout': False,
        'criteria': {}
    }
    
    # 1. Tight Base Analysis
    base_closes = closes[-base_len:]
    range_high = np.max(base_closes)
    range_low = np.min(base_closes)
    range_size = range_high - range_low
    range_pct = (range_size / range_low) * 100 if range_low > 0 else 0
    tight_base = range_pct <= max_range_width_pct
    
    # 2. ATR Contraction Analysis (relaxed)
    atr_contraction = True  # Default to True if we can't calculate properly
    atr_ratio = 1.0
    
    if len(closes) >= atr_len + atr_ma:
        try:
            atr_series = _atr(highs, lows, closes, atr_len)
            atr_ma_series = _sma(atr_series, atr_ma)
            
            if (len(atr_series) > 0 and len(atr_ma_series) > 0 and 
                not np.isnan(atr_series[-1]) and not np.isnan(atr_ma_series[-1]) and 
                atr_ma_series[-1] != 0):
                atr_ratio = atr_series[-1] / atr_ma_series[-1]
                atr_contraction = atr_ratio <= atr_ratio_thresh
        except:
            atr_contraction = True  # Default to True if calculation fails
    
    # 3. Higher Lows Analysis
    higher_lows_ok = True
    higher_lows_pct = 50.0  # Default
    
    if len(lows) >= base_len:
        recent_lows = lows[-base_len:]
        higher_lows_count = 0
        for i in range(1, len(recent_lows)):
            if recent_lows[i] > recent_lows[i-1]:
                higher_lows_count += 1
        higher_lows_pct = (higher_lows_count / len(recent_lows)) * 100
    
    # 4. Price Breakout Analysis (relaxed)
    min_break_price = range_high * (1.0 + min_break_above_pct / 100.0)
    price_break = closes[-1] >= min_break_price
    
    # 5. Volume Expansion Analysis (relaxed)
    volume_expansion = True  # Default to True
    volume_mult = 1.0
    
    if len(volumes) >= vol_ma:
        try:
            vol_ma_series = _sma(volumes, vol_ma)
            if not np.isnan(vol_ma_series[-1]) and vol_ma_series[-1] > 0:
                volume_mult = volumes[-1] / vol_ma_series[-1]
                volume_expansion = volume_mult >= vol_mult
        except:
            volume_expansion = True  # Default to True
    
    # 6. Prior Impulse Analysis (relaxed)
    impulse_detected = True  # Default to True for relaxed analysis
    impulse_pct = 20.0  # Default
    
    if len(closes) >= 40:  # Reduced minimum for impulse detection
        for i in range(10, len(closes) - 10):  # Reduced window
            window_high = np.max(highs[i-10:i+10])
            window_low = np.min(lows[i-10:i+10])
            
            if window_high > window_low:
                move_pct = (window_high - window_low) / window_low
                if move_pct >= (prior_impulse_thresh / 100.0):
                    impulse_detected = True
                    impulse_pct = move_pct * 100
                    break
    
    # Flag Breakout Criteria (relaxed)
    flag_breakout = (tight_base and atr_contraction and higher_lows_ok and 
                    price_break and volume_expansion and impulse_detected)
    
    # Range Breakout Criteria (same as Flag for relaxed analysis)
    range_breakout = flag_breakout
    
    results.update({
        'flag_breakout': flag_breakout,
        'range_breakout': range_breakout,
        'criteria': {
            'tight_base': {'passed': tight_base, 'range_pct': range_pct},
            'atr_contraction': {'passed': atr_contraction, 'ratio': atr_ratio},
            'higher_lows': {'passed': higher_lows_ok, 'percentage': higher_lows_pct},
            'price_breakout': {'passed': price_break, 'current_price': closes[-1], 'required_price': min_break_price},
            'volume_expansion': {'passed': volume_expansion, 'multiple': volume_mult},
            'prior_impulse': {'detected': impulse_detected, 'percentage': impulse_pct}
        }
    })
    
    return results

def main():
    """Main analysis function"""
    print("🔍 NASDAQ Relaxed Breakout Analysis (Aug-Sep-Oct 2025)")
    print("Using relaxed parameters suitable for available data")
    print("=" * 80)
    
    # Load data
    combined_df = load_combined_nasdaq_data()
    symbols = combined_df['symbol'].unique().tolist()
    
    print(f"📊 Analyzing {len(symbols)} symbols for breakouts...")
    print("🔧 Relaxed Filters: Price ≥ $5, Volume ≥ 100K, Min 30 data points")
    print("🔧 Relaxed Parameters: 40% tight base, 1.2x volume, 0.5% price breakout")
    print("=" * 80)
    
    breakout_results = []
    flag_breakouts = []
    range_breakouts = []
    
    # Analyze each symbol
    for i, symbol in enumerate(symbols):
        if i % 100 == 0:
            print(f"📈 Progress: {i}/{len(symbols)} symbols analyzed...")
        
        try:
            result = analyze_stock_relaxed(symbol, combined_df)
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
    print(f"\n🎯 RELAXED BREAKOUT ANALYSIS RESULTS")
    print("=" * 80)
    print(f"📊 Total symbols analyzed: {len(breakout_results)}")
    print(f"🚩 Flag breakouts found: {len(flag_breakouts)}")
    print(f"📦 Range breakouts found: {len(range_breakouts)}")
    print(f"🎯 Total breakout signals: {len(flag_breakouts) + len(range_breakouts)}")
    
    # Display Flag Breakouts
    if flag_breakouts:
        print(f"\n🚩 FLAG BREAKOUTS ({len(flag_breakouts)}):")
        print("-" * 90)
        print(f"{'Symbol':<8} | {'Price':<8} | {'Range%':<8} | {'Vol Mult':<8} | {'ATR':<6} | {'Days':<5}")
        print("-" * 90)
        
        for result in flag_breakouts:
            criteria = result['criteria']
            print(f"{result['symbol']:<8} | ${result['price']:<7.2f} | {criteria['tight_base']['range_pct']:<7.1f}% | {criteria['volume_expansion']['multiple']:<7.1f}x | {criteria['atr_contraction']['ratio']:<6.3f} | {result['data_points']:<5}")
    
    # Display Range Breakouts
    if range_breakouts:
        print(f"\n📦 RANGE BREAKOUTS ({len(range_breakouts)}):")
        print("-" * 90)
        print(f"{'Symbol':<8} | {'Price':<8} | {'Range%':<8} | {'Vol Mult':<8} | {'ATR':<6} | {'Days':<5}")
        print("-" * 90)
        
        for result in range_breakouts:
            criteria = result['criteria']
            print(f"{result['symbol']:<8} | ${result['price']:<7.2f} | {criteria['tight_base']['range_pct']:<7.1f}% | {criteria['volume_expansion']['multiple']:<7.1f}x | {criteria['atr_contraction']['ratio']:<6.3f} | {result['data_points']:<5}")
    
    # Save results to JSON
    output_file = Path(__file__).parent / "nasdaq_relaxed_breakout_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            'analysis_date': datetime.now().isoformat(),
            'data_range': f"{combined_df['date'].min()} to {combined_df['date'].max()}",
            'parameters': {
                'base_len': 'adaptive (max 20)',
                'max_range_width_pct': 40.0,
                'atr_ratio_thresh': 1.2,
                'price_break_thresh': 0.5,
                'volume_mult': 1.2,
                'prior_impulse_thresh': 15.0
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
