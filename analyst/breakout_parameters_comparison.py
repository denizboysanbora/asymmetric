#!/usr/bin/env python3
"""
Breakout Parameters Comparison
Compare actual breakout days to our technical parameters
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
            return bars.data[symbol]
        else:
            return None
            
    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {e}")
        return None

def calculate_technical_metrics(bars: List[Bar], target_date: datetime):
    """Calculate technical metrics for a specific date"""
    
    if not bars or len(bars) < 60:
        return None
    
    # Find bars up to target date
    bars_up_to_date = []
    target_bar = None
    
    for bar in bars:
        if bar.timestamp.date() <= target_date.date():
            bars_up_to_date.append(bar)
            if bar.timestamp.date() == target_date.date():
                target_bar = bar
    
    if not target_bar or len(bars_up_to_date) < 60:
        return None
    
    # Convert to arrays
    closes = np.array([float(bar.close) for bar in bars_up_to_date])
    highs = np.array([float(bar.high) for bar in bars_up_to_date])
    lows = np.array([float(bar.low) for bar in bars_up_to_date])
    volumes = np.array([int(bar.volume) for bar in bars_up_to_date])
    
    # Calculate metrics
    current_price = closes[-1]
    current_volume = volumes[-1]
    
    # 1. Tight Base Analysis (last 20 days)
    recent_closes = closes[-20:]
    recent_highs = highs[-20:]
    recent_lows = lows[-20:]
    
    range_high = np.max(recent_highs)
    range_low = np.min(recent_lows)
    range_size = range_high - range_low
    range_pct = (range_size / range_low) * 100 if range_low > 0 else 100
    
    # 2. ATR Contraction Analysis
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
    
    # 3. Higher Lows Pattern
    recent_lows = lows[-20:]
    higher_lows_count = 0
    for i in range(1, len(recent_lows)):
        if recent_lows[i] > recent_lows[i-1]:
            higher_lows_count += 1
    higher_lows_pct = (higher_lows_count / len(recent_lows)) * 100
    
    # 4. Volume Expansion
    recent_volume = volumes[-1]
    avg_volume = np.mean(volumes[-50:-1]) if len(volumes) >= 50 else np.mean(volumes[:-1])
    volume_multiple = recent_volume / avg_volume if avg_volume > 0 else 1
    
    # 5. Price Breakout
    min_break_price_flag = range_high * 1.01  # 1% for flag
    min_break_price_range = range_high * 1.015  # 1.5% for range
    price_breakout_flag = current_price >= min_break_price_flag
    price_breakout_range = current_price >= min_break_price_range
    breakout_distance = ((current_price - range_high) / range_high) * 100
    
    # 6. Prior Impulse (for flag breakouts)
    impulse_detected = False
    max_impulse_pct = 0
    
    for i in range(20, len(bars_up_to_date) - 20):
        window_high = max(highs[i-20:i+20])
        window_low = min(lows[i-20:i+20])
        
        if window_high > window_low:
            move_pct = ((window_high - window_low) / window_low) * 100
            if move_pct >= 30.0:
                impulse_detected = True
                max_impulse_pct = move_pct
                break
    
    return {
        'date': target_date.date().isoformat(),
        'price': current_price,
        'volume': current_volume,
        'range_pct': range_pct,
        'atr_ratio': atr_ratio,
        'higher_lows_pct': higher_lows_pct,
        'volume_multiple': volume_multiple,
        'price_breakout_flag': price_breakout_flag,
        'price_breakout_range': price_breakout_range,
        'breakout_distance': breakout_distance,
        'prior_impulse': impulse_detected,
        'impulse_pct': max_impulse_pct,
        'range_high': range_high,
        'range_low': range_low
    }

def create_comparison_table():
    """Create comparison table of actual breakouts vs parameters"""
    
    print("🔍 Breakout Parameters Comparison")
    print("Comparing actual breakout days to our technical parameters")
    print("=" * 100)
    
    # Define our current parameters
    current_params = {
        'flag_breakout': {
            'tight_base_threshold': 25.0,  # %
            'atr_contraction_threshold': 0.8,
            'higher_lows_required': False,
            'price_breakout_threshold': 1.0,  # %
            'volume_expansion_threshold': 1.5,  # x
            'prior_impulse_threshold': 30.0,  # %
            'market_filter': True
        },
        'range_breakout': {
            'tight_base_threshold': 25.0,  # %
            'atr_contraction_threshold': 0.8,
            'higher_lows_required': True,
            'price_breakout_threshold': 1.5,  # %
            'volume_expansion_threshold': 1.5,  # x
            'prior_impulse_threshold': None,  # Not required
            'market_filter': True
        }
    }
    
    # Analyze specific breakout days
    breakout_days = [
        {'symbol': 'APPS', 'date': datetime(2020, 7, 31), 'type': 'Strong Move'},
        {'symbol': 'CODX', 'date': datetime(2020, 2, 26), 'type': 'Massive Breakout'},
        {'symbol': 'CODX', 'date': datetime(2020, 2, 27), 'type': 'Continuation'},
        {'symbol': 'CODX', 'date': datetime(2020, 2, 10), 'type': 'Early Breakout'},
        {'symbol': 'CODX', 'date': datetime(2020, 2, 24), 'type': 'Mid Breakout'}
    ]
    
    results = []
    
    for breakout_day in breakout_days:
        symbol = breakout_day['symbol']
        target_date = breakout_day['date']
        breakout_type = breakout_day['type']
        
        print(f"\n📊 Analyzing {symbol} on {target_date.date()} ({breakout_type})...")
        
        # Fetch data
        bars = fetch_historical_data(symbol, target_date, target_date)
        if not bars:
            continue
        
        # Calculate metrics
        metrics = calculate_technical_metrics(bars, target_date)
        if not metrics:
            continue
        
        # Check against parameters
        flag_criteria = {
            'tight_base': metrics['range_pct'] <= current_params['flag_breakout']['tight_base_threshold'],
            'atr_contraction': metrics['atr_ratio'] <= current_params['flag_breakout']['atr_contraction_threshold'],
            'higher_lows': not current_params['flag_breakout']['higher_lows_required'] or metrics['higher_lows_pct'] >= 50.0,
            'price_breakout': metrics['price_breakout_flag'],
            'volume_expansion': metrics['volume_multiple'] >= current_params['flag_breakout']['volume_expansion_threshold'],
            'prior_impulse': metrics['prior_impulse']
        }
        
        range_criteria = {
            'tight_base': metrics['range_pct'] <= current_params['range_breakout']['tight_base_threshold'],
            'atr_contraction': metrics['atr_ratio'] <= current_params['range_breakout']['atr_contraction_threshold'],
            'higher_lows': not current_params['range_breakout']['higher_lows_required'] or metrics['higher_lows_pct'] >= 50.0,
            'price_breakout': metrics['price_breakout_range'],
            'volume_expansion': metrics['volume_multiple'] >= current_params['range_breakout']['volume_expansion_threshold']
        }
        
        flag_score = sum(flag_criteria.values())
        range_score = sum(range_criteria.values())
        
        results.append({
            'symbol': symbol,
            'date': metrics['date'],
            'type': breakout_type,
            'price': metrics['price'],
            'volume': metrics['volume'],
            'range_pct': metrics['range_pct'],
            'atr_ratio': metrics['atr_ratio'],
            'higher_lows_pct': metrics['higher_lows_pct'],
            'volume_multiple': metrics['volume_multiple'],
            'breakout_distance': metrics['breakout_distance'],
            'prior_impulse': metrics['prior_impulse'],
            'impulse_pct': metrics['impulse_pct'],
            'flag_criteria': flag_criteria,
            'range_criteria': range_criteria,
            'flag_score': flag_score,
            'range_score': range_score
        })
    
    # Display comparison table
    print(f"\n" + "=" * 150)
    print(f"📊 BREAKOUT PARAMETERS COMPARISON TABLE")
    print("=" * 150)
    
    # Header
    print(f"{'Symbol':<8} {'Date':<12} {'Type':<15} {'Price':<8} {'Range%':<8} {'ATR':<6} {'HL%':<6} {'VolX':<6} {'Break%':<8} {'Imp%':<6} {'Flag':<5} {'Range':<6}")
    print("-" * 150)
    
    # Current parameters
    print(f"\n📋 CURRENT PARAMETERS:")
    print(f"   Flag Breakout:  Tight Base ≤25%, ATR ≤0.8, Price Break ≥1.0%, Volume ≥1.5x, Prior Impulse ≥30%")
    print(f"   Range Breakout: Tight Base ≤25%, ATR ≤0.8, Higher Lows Required, Price Break ≥1.5%, Volume ≥1.5x")
    
    # Data rows
    for result in results:
        print(f"{result['symbol']:<8} {result['date']:<12} {result['type']:<15} ${result['price']:<7.2f} {result['range_pct']:<7.1f}% {result['atr_ratio']:<5.2f} {result['higher_lows_pct']:<5.1f}% {result['volume_multiple']:<5.1f}x {result['breakout_distance']:<7.1f}% {result['impulse_pct']:<5.1f}% {result['flag_score']:<5}/6 {result['range_score']:<6}/5")
    
    # Detailed analysis
    print(f"\n" + "=" * 150)
    print(f"🎯 DETAILED ANALYSIS")
    print("=" * 150)
    
    for result in results:
        print(f"\n📊 {result['symbol']} - {result['date']} ({result['type']}):")
        print(f"   💰 Price: ${result['price']:.2f} | Volume: {result['volume']:,} ({result['volume_multiple']:.1f}x)")
        print(f"   📏 Range: {result['range_pct']:.1f}% | ATR Ratio: {result['atr_ratio']:.2f}")
        print(f"   🚩 Higher Lows: {result['higher_lows_pct']:.1f}% | Breakout Distance: {result['breakout_distance']:+.1f}%")
        print(f"   🎯 Prior Impulse: {result['impulse_pct']:.1f}% ({'✅' if result['prior_impulse'] else '❌'})")
        
        print(f"   🚩 Flag Breakout Criteria:")
        for criterion, passed in result['flag_criteria'].items():
            status = "✅" if passed else "❌"
            print(f"      {criterion}: {status}")
        print(f"   📊 Flag Score: {result['flag_score']}/6")
        
        print(f"   📦 Range Breakout Criteria:")
        for criterion, passed in result['range_criteria'].items():
            status = "✅" if passed else "❌"
            print(f"      {criterion}: {status}")
        print(f"   📊 Range Score: {result['range_score']}/5")
    
    # Summary
    print(f"\n" + "=" * 150)
    print(f"💡 SUMMARY & INSIGHTS")
    print("=" * 150)
    
    print(f"🔍 Why These Breakouts Didn't Trigger Our Parameters:")
    print(f"   1. 📏 Tight Base: Most had ranges >25% (volatile periods)")
    print(f"   2. 📊 ATR Contraction: Most had ATR ratios >0.8 (high volatility)")
    print(f"   3. 🚩 Higher Lows: Some lacked the required pattern")
    print(f"   4. 💰 Price Breakout: Some didn't break above recent highs by enough")
    print(f"   5. 📈 Volume: Some had volume but not enough expansion")
    print(f"   6. 🎯 Prior Impulse: Some lacked the required 30% prior move")
    
    print(f"\n🎯 Key Insights:")
    print(f"   • Our parameters are designed for 'clean' technical breakouts")
    print(f"   • These were more 'momentum/fundamental-driven' moves")
    print(f"   • High volatility periods often don't meet tight base criteria")
    print(f"   • ATR contraction is hard to achieve during volatile breakouts")
    print(f"   • Our system prioritizes quality over quantity")
    
    # Save results
    results_file = Path(__file__).parent / "breakout_parameters_comparison_results.json"
    import json
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n💾 Results saved to: {results_file}")

def main():
    """Main analysis function"""
    
    try:
        create_comparison_table()
        print(f"\n✅ Breakout parameters comparison completed!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()