#!/usr/bin/env python3
"""
NASDAQ Breakout Diagnostic Analysis
Shows detailed breakdown of why stocks don't qualify for breakouts
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

def analyze_stock_diagnostic(symbol: str, combined_df: pd.DataFrame, min_price: float = 5.0, min_volume: int = 100000):
    """Detailed diagnostic analysis of why a stock doesn't qualify for breakouts"""
    
    symbol_data = combined_df[combined_df['symbol'] == symbol].copy()
    
    if symbol_data.empty or len(symbol_data) < 40:
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
    
    # Parameters
    base_len = 20
    max_range_width_pct = 25.0
    atr_len = 14
    atr_ma = 50
    atr_ratio_thresh = 0.9  # Flag threshold
    min_break_above_pct = 1.0  # Flag threshold
    vol_ma = 50
    vol_mult = 1.5
    
    # 1. Tight Base Analysis
    base_closes = closes[-base_len:]
    range_high = np.max(base_closes)
    range_low = np.min(base_closes)
    range_size = range_high - range_low
    range_pct = (range_size / range_low) * 100
    tight_base = range_pct <= max_range_width_pct
    
    # 2. ATR Contraction Analysis
    atr_series = _atr(highs, lows, closes, atr_len)
    atr_ma_series = _sma(atr_series, atr_ma)
    
    if len(atr_series) > 0 and len(atr_ma_series) > 0 and not np.isnan(atr_series[-1]) and not np.isnan(atr_ma_series[-1]) and atr_ma_series[-1] != 0:
        atr_ratio = atr_series[-1] / atr_ma_series[-1]
        atr_contraction = atr_ratio <= atr_ratio_thresh
    else:
        atr_ratio = np.nan
        atr_contraction = False
    
    # 3. Higher Lows Analysis (for Flag - optional)
    higher_lows_ok = True  # Optional for Flag
    if len(lows) >= base_len:
        recent_lows = lows[-base_len:]
        higher_lows_count = 0
        for i in range(1, len(recent_lows)):
            if recent_lows[i] > recent_lows[i-1]:
                higher_lows_count += 1
        higher_lows_pct = (higher_lows_count / len(recent_lows)) * 100
    else:
        higher_lows_pct = 0
    
    # 4. Price Breakout Analysis
    min_break_price = range_high * (1.0 + min_break_above_pct / 100.0)
    price_break = closes[-1] >= min_break_price
    
    # 5. Volume Expansion Analysis
    if len(volumes) >= vol_ma:
        vol_ma_series = _sma(volumes, vol_ma)
        if not np.isnan(vol_ma_series[-1]) and vol_ma_series[-1] > 0:
            volume_mult = volumes[-1] / vol_ma_series[-1]
            volume_expansion = volume_mult >= vol_mult
        else:
            volume_mult = 0
            volume_expansion = False
    else:
        volume_mult = 0
        volume_expansion = False
    
    # 6. Prior Impulse Analysis (for Flag)
    impulse_detected = False
    impulse_pct = 0
    
    if len(closes) >= 60:
        for i in range(20, len(closes) - 20):
            window_high = np.max(highs[i-20:i+20])
            window_low = np.min(lows[i-20:i+20])
            
            if window_high > window_low:
                move_pct = (window_high - window_low) / window_low
                if move_pct >= 0.30:  # 30%+ move
                    impulse_detected = True
                    impulse_pct = move_pct * 100
                    break
    
    return {
        'symbol': symbol,
        'price': latest['close'],
        'volume': latest['volume'],
        'date': latest['date'],
        'data_points': len(symbol_data),
        'tight_base': {
            'passed': tight_base,
            'range_pct': range_pct,
            'range_high': range_high,
            'range_low': range_low
        },
        'atr_contraction': {
            'passed': atr_contraction,
            'ratio': atr_ratio,
            'threshold': atr_ratio_thresh
        },
        'higher_lows': {
            'passed': higher_lows_ok,
            'percentage': higher_lows_pct
        },
        'price_breakout': {
            'passed': price_break,
            'current_price': closes[-1],
            'required_price': min_break_price,
            'breakout_pct': ((closes[-1] - range_high) / range_high * 100) if range_high > 0 else 0
        },
        'volume_expansion': {
            'passed': volume_expansion,
            'multiple': volume_mult,
            'threshold': vol_mult
        },
        'prior_impulse': {
            'detected': impulse_detected,
            'percentage': impulse_pct
        }
    }

def main():
    """Main diagnostic function"""
    print("🔍 NASDAQ Breakout Diagnostic Analysis")
    print("Shows detailed breakdown of why stocks don't qualify for breakouts")
    print("=" * 80)
    
    # Load data
    combined_df = load_combined_nasdaq_data()
    symbols = combined_df['symbol'].unique().tolist()
    
    print(f"📊 Analyzing {len(symbols)} symbols...")
    print("🔧 Filters: Price ≥ $5, Volume ≥ 100K, Min 40 data points")
    print("=" * 80)
    
    # Analyze top 20 symbols by volume for diagnostic
    symbol_volumes = []
    for symbol in symbols[:100]:  # Check first 100 symbols
        symbol_data = combined_df[combined_df['symbol'] == symbol]
        if not symbol_data.empty:
            latest_volume = symbol_data.iloc[-1]['volume']
            symbol_volumes.append((symbol, latest_volume))
    
    # Sort by volume descending
    symbol_volumes.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n📊 DIAGNOSTIC RESULTS (Top 10 by Volume):")
    print("=" * 100)
    
    for i, (symbol, volume) in enumerate(symbol_volumes[:10]):
        result = analyze_stock_diagnostic(symbol, combined_df)
        if result:
            print(f"\n{i+1}. {result['symbol']} - ${result['price']:.2f} (Vol: {result['volume']:,})")
            print(f"   Data Points: {result['data_points']}")
            print(f"   📏 Tight Base: {'✅' if result['tight_base']['passed'] else '❌'} ({result['tight_base']['range_pct']:.1f}% range)")
            print(f"   📊 ATR Contraction: {'✅' if result['atr_contraction']['passed'] else '❌'} (Ratio: {result['atr_contraction']['ratio']:.3f})")
            print(f"   🚩 Higher Lows: {'✅' if result['higher_lows']['passed'] else '❌'} ({result['higher_lows']['percentage']:.1f}%)")
            print(f"   💰 Price Breakout: {'✅' if result['price_breakout']['passed'] else '❌'} (${result['price_breakout']['current_price']:.2f} vs ${result['price_breakout']['required_price']:.2f})")
            print(f"   📈 Volume Expansion: {'✅' if result['volume_expansion']['passed'] else '❌'} ({result['volume_expansion']['multiple']:.1f}x)")
            print(f"   🎯 Prior Impulse: {'✅' if result['prior_impulse']['detected'] else '❌'} ({result['prior_impulse']['percentage']:.1f}%)")
            
            # Overall Flag Breakout potential
            flag_potential = (result['tight_base']['passed'] and 
                            result['atr_contraction']['passed'] and 
                            result['higher_lows']['passed'] and 
                            result['price_breakout']['passed'] and 
                            result['volume_expansion']['passed'] and 
                            result['prior_impulse']['detected'])
            
            print(f"   🚩 FLAG BREAKOUT: {'✅ PASS' if flag_potential else '❌ FAIL'}")

if __name__ == "__main__":
    main()
