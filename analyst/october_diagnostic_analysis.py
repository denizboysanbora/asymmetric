#!/usr/bin/env python3
"""
October 2025 Diagnostic Analysis
Analyzes why no breakouts were found and shows top candidates with relaxed parameters
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

def load_sample_data():
    """Load sample data from the database"""
    
    db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq.db"
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return None, None
    
    conn = sqlite3.connect(db_path)
    
    # Get sample of symbols with good volume and price
    sample_query = """
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
    LIMIT 50
    """
    
    symbols_df = pd.read_sql_query(sample_query, conn)
    symbols = symbols_df['symbol'].tolist()
    
    print(f"📊 Analyzing sample of {len(symbols)} symbols")
    
    conn.close()
    return symbols

def get_stock_data(symbol: str):
    """Get stock data for a specific symbol"""
    
    db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq.db"
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

def analyze_diagnostic_criteria(bars: List, symbol: str):
    """Analyze diagnostic criteria for a stock"""
    
    if not bars or len(bars) < 60:
        return None
    
    closes = [bar.close for bar in bars]
    highs = [bar.high for bar in bars]
    lows = [bar.low for bar in bars]
    volumes = [bar.volume for bar in bars]
    
    # Current price and volume
    current_price = closes[-1]
    current_volume = volumes[-1]
    
    # Calculate diagnostic metrics
    diagnostics = {
        'symbol': symbol,
        'price': current_price,
        'volume': current_volume,
        'data_points': len(bars),
        
        # Tight base analysis (last 20 days)
        'tight_base': None,
        'tight_base_pct': None,
        
        # ATR contraction analysis
        'atr_contraction': None,
        'atr_ratio': None,
        
        # Higher lows pattern
        'higher_lows': None,
        'higher_lows_pct': None,
        
        # Price breakout analysis
        'price_breakout': None,
        'breakout_distance': None,
        
        # Volume expansion
        'volume_expansion': None,
        'volume_multiple': None,
        
        # Prior impulse (for flag breakouts)
        'prior_impulse': None,
        'impulse_pct': None
    }
    
    # 1. Tight Base Analysis (last 20 days)
    if len(closes) >= 20:
        recent_closes = closes[-20:]
        recent_highs = highs[-20:]
        recent_lows = lows[-20:]
        
        range_high = max(recent_highs)
        range_low = min(recent_lows)
        range_size = range_high - range_low
        range_pct = (range_size / range_low) * 100 if range_low > 0 else 100
        
        diagnostics['tight_base_pct'] = range_pct
        diagnostics['tight_base'] = range_pct <= 25.0  # 25% threshold
        
        # Price breakout check
        min_break_price = range_high * 1.015  # 1.5% above recent high
        diagnostics['price_breakout'] = current_price >= min_break_price
        diagnostics['breakout_distance'] = ((current_price - range_high) / range_high) * 100
    
    # 2. ATR Contraction Analysis
    if len(closes) >= 50:
        # Calculate ATR for recent vs baseline
        def calculate_atr(h, l, c, period):
            tr_values = []
            for i in range(1, len(c)):
                tr = max(
                    h[i] - l[i],
                    abs(h[i] - c[i-1]),
                    abs(l[i] - c[i-1])
                )
                tr_values.append(tr)
            return np.mean(tr_values[-period:]) if tr_values else 0
        
        recent_atr = calculate_atr(highs, lows, closes, 14)
        baseline_atr = calculate_atr(highs[:30], lows[:30], closes[:30], 14)
        
        atr_ratio = recent_atr / baseline_atr if baseline_atr > 0 else 1
        diagnostics['atr_ratio'] = atr_ratio
        diagnostics['atr_contraction'] = atr_ratio <= 0.8
    
    # 3. Higher Lows Pattern
    if len(lows) >= 20:
        recent_lows = lows[-20:]
        higher_lows_count = 0
        for i in range(1, len(recent_lows)):
            if recent_lows[i] > recent_lows[i-1]:
                higher_lows_count += 1
        
        higher_lows_pct = (higher_lows_count / len(recent_lows)) * 100
        diagnostics['higher_lows_pct'] = higher_lows_pct
        diagnostics['higher_lows'] = higher_lows_pct >= 50.0
    
    # 4. Volume Expansion
    if len(volumes) >= 50:
        recent_volume = volumes[-1]
        avg_volume = np.mean(volumes[-50:-1])  # 50-day average excluding today
        volume_multiple = recent_volume / avg_volume if avg_volume > 0 else 1
        
        diagnostics['volume_multiple'] = volume_multiple
        diagnostics['volume_expansion'] = volume_multiple >= 1.5
    
    # 5. Prior Impulse (for flag breakouts)
    if len(closes) >= 60:
        # Look for 30%+ move in last 60 days
        impulse_detected = False
        max_impulse_pct = 0
        
        for i in range(20, len(bars) - 20):
            window_high = max(highs[i-20:i+20])
            window_low = min(lows[i-20:i+20])
            
            if window_high > window_low:
                move_pct = ((window_high - window_low) / window_low) * 100
                if move_pct >= 30.0:
                    impulse_detected = True
                    max_impulse_pct = move_pct
                    break
        
        diagnostics['prior_impulse'] = impulse_detected
        diagnostics['impulse_pct'] = max_impulse_pct
    
    return diagnostics

def run_diagnostic_analysis():
    """Run diagnostic analysis on sample symbols"""
    
    print("🔍 October 2025 Diagnostic Analysis")
    print("Analyzing why no breakouts were found")
    print("=" * 70)
    
    symbols = load_sample_data()
    if not symbols:
        return
    
    all_diagnostics = []
    
    for i, symbol in enumerate(symbols):
        if i % 10 == 0:
            print(f"📈 Progress: {i}/{len(symbols)} symbols analyzed...")
        
        bars = get_stock_data(symbol)
        if not bars:
            continue
        
        diagnostics = analyze_diagnostic_criteria(bars, symbol)
        if diagnostics:
            all_diagnostics.append(diagnostics)
    
    if not all_diagnostics:
        print("❌ No diagnostic data collected")
        return
    
    # Analyze results
    print("\n" + "=" * 70)
    print("🎯 DIAGNOSTIC ANALYSIS RESULTS")
    print("=" * 70)
    
    total_analyzed = len(all_diagnostics)
    print(f"📊 Total symbols analyzed: {total_analyzed}")
    
    # Count criteria failures
    criteria_counts = {
        'tight_base': sum(1 for d in all_diagnostics if d['tight_base']),
        'atr_contraction': sum(1 for d in all_diagnostics if d['atr_contraction']),
        'higher_lows': sum(1 for d in all_diagnostics if d['higher_lows']),
        'price_breakout': sum(1 for d in all_diagnostics if d['price_breakout']),
        'volume_expansion': sum(1 for d in all_diagnostics if d['volume_expansion']),
        'prior_impulse': sum(1 for d in all_diagnostics if d['prior_impulse'])
    }
    
    print(f"\n📊 Criteria Analysis:")
    print(f"   📏 Tight Base (≤25%): {criteria_counts['tight_base']}/{total_analyzed} ({criteria_counts['tight_base']/total_analyzed*100:.1f}%)")
    print(f"   📊 ATR Contraction (≤0.8): {criteria_counts['atr_contraction']}/{total_analyzed} ({criteria_counts['atr_contraction']/total_analyzed*100:.1f}%)")
    print(f"   🚩 Higher Lows (≥50%): {criteria_counts['higher_lows']}/{total_analyzed} ({criteria_counts['higher_lows']/total_analyzed*100:.1f}%)")
    print(f"   💰 Price Breakout (≥1.5%): {criteria_counts['price_breakout']}/{total_analyzed} ({criteria_counts['price_breakout']/total_analyzed*100:.1f}%)")
    print(f"   📈 Volume Expansion (≥1.5x): {criteria_counts['volume_expansion']}/{total_analyzed} ({criteria_counts['volume_expansion']/total_analyzed*100:.1f}%)")
    print(f"   🎯 Prior Impulse (≥30%): {criteria_counts['prior_impulse']}/{total_analyzed} ({criteria_counts['prior_impulse']/total_analyzed*100:.1f}%)")
    
    # Show top candidates with relaxed criteria
    print(f"\n🏆 TOP CANDIDATES (Relaxed Criteria):")
    print("-" * 70)
    
    # Sort by number of criteria met
    for diagnostics in all_diagnostics:
        criteria_met = sum([
            diagnostics['tight_base'] or False,
            diagnostics['atr_contraction'] or False,
            diagnostics['higher_lows'] or False,
            diagnostics['price_breakout'] or False,
            diagnostics['volume_expansion'] or False
        ])
        diagnostics['criteria_met'] = criteria_met
    
    # Sort by criteria met (descending)
    sorted_diagnostics = sorted(all_diagnostics, key=lambda x: x['criteria_met'], reverse=True)
    
    # Show top 10 candidates
    for i, d in enumerate(sorted_diagnostics[:10]):
        print(f"{i+1:2d}. {d['symbol']:<8} ${d['price']:>8.2f} (Vol: {d['volume']:>8,})")
        print(f"     Criteria: {d['criteria_met']}/5 met")
        
        if d['tight_base_pct'] is not None:
            print(f"     📏 Tight Base: {d['tight_base_pct']:.1f}% {'✅' if d['tight_base'] else '❌'}")
        if d['atr_ratio'] is not None:
            print(f"     📊 ATR Ratio: {d['atr_ratio']:.2f} {'✅' if d['atr_contraction'] else '❌'}")
        if d['higher_lows_pct'] is not None:
            print(f"     🚩 Higher Lows: {d['higher_lows_pct']:.1f}% {'✅' if d['higher_lows'] else '❌'}")
        if d['breakout_distance'] is not None:
            print(f"     💰 Breakout: {d['breakout_distance']:+.1f}% {'✅' if d['price_breakout'] else '❌'}")
        if d['volume_multiple'] is not None:
            print(f"     📈 Volume: {d['volume_multiple']:.1f}x {'✅' if d['volume_expansion'] else '❌'}")
        if d['impulse_pct'] is not None:
            print(f"     🎯 Prior Impulse: {d['impulse_pct']:.1f}% {'✅' if d['prior_impulse'] else '❌'}")
        print()
    
    # Save detailed results
    results_file = Path(__file__).parent / "october_diagnostic_results.json"
    import json
    with open(results_file, 'w') as f:
        json.dump(all_diagnostics, f, indent=2, default=str)
    
    print(f"💾 Detailed results saved to: {results_file}")

def main():
    """Main diagnostic function"""
    
    try:
        run_diagnostic_analysis()
        print("\n✅ Diagnostic analysis completed!")
        
    except Exception as e:
        print(f"❌ Error during diagnostic analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
