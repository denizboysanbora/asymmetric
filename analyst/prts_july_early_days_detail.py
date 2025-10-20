#!/usr/bin/env python3
"""
PRTS July 2020 - Early Days Detailed Analysis
Specific breakdown for July 1, 2, 6, and 7
"""
import os
import sys
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Load environment variables
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / "config" / "api_keys.env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

# Add alpaca directory to path
ALPACA_DIR = Path(__file__).parent / "input" / "alpaca"
sys.path.insert(0, str(ALPACA_DIR))

try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.models import Bar
except ImportError as e:
    print(f"Error importing Alpaca modules: {e}")
    sys.exit(1)

def get_july_data():
    """Get all PRTS data for July 2020"""
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    client = StockHistoricalDataClient(api_key, secret_key)
    
    # Get extended data for analysis
    request = StockBarsRequest(
        symbol_or_symbols="PRTS",
        timeframe=TimeFrame.Day,
        start=datetime(2020, 1, 1),  # Start from January to get enough history
        end=datetime(2020, 7, 31)
    )
    
    bars = client.get_stock_bars(request)
    return bars.data["PRTS"]

def analyze_specific_days(bars: List[Bar], target_dates: List[str]):
    """Analyze specific days in detail"""
    
    # Get July bars and sort by date
    july_bars = [bar for bar in bars if bar.timestamp.month == 7 and bar.timestamp.year == 2020]
    july_bars.sort(key=lambda x: x.timestamp.date())
    
    print("📊 PRTS JULY 2020 - EARLY DAYS DETAILED ANALYSIS")
    print("=" * 90)
    print(f"📅 Target Dates: {', '.join(target_dates)}")
    print("=" * 90)
    
    for target_date_str in target_dates:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        
        # Find the bar for this date
        target_bar = None
        for bar in july_bars:
            if bar.timestamp.date() == target_date:
                target_bar = bar
                break
        
        if not target_bar:
            print(f"❌ No data found for {target_date}")
            continue
        
        # Get historical data up to this point
        historical_bars = [b for b in bars if b.timestamp.date() <= target_date]
        
        if len(historical_bars) < 60:
            print(f"⚠️  {target_date} - Insufficient historical data ({len(historical_bars)} bars)")
            continue
        
        # Calculate daily change
        price = float(target_bar.close)
        volume = float(target_bar.volume)
        
        # Find previous day's close
        prev_price = None
        for i, bar in enumerate(july_bars):
            if bar.timestamp.date() == target_date:
                if i > 0:
                    prev_price = float(july_bars[i-1].close)
                break
        
        if prev_price:
            daily_change = (price - prev_price) / prev_price * 100
        else:
            daily_change = 0.0
        
        print(f"\n📅 {target_date} - ${price:.2f} ({daily_change:+.1f}%) | Vol: {volume:,.0f}")
        print("=" * 80)
        
        # Detailed analysis
        analyze_day_in_detail(historical_bars, price, volume, target_date)

def analyze_day_in_detail(bars: List[Bar], current_price: float, current_volume: float, date):
    """Detailed analysis for a specific day"""
    
    closes = np.array([float(bar.close) for bar in bars])
    highs = np.array([float(bar.high) for bar in bars])
    lows = np.array([float(bar.low) for bar in bars])
    volumes = np.array([float(bar.volume) for bar in bars])
    
    print("🔍 DETAILED BREAKOUT ANALYSIS:")
    print("-" * 60)
    
    # FLAG BREAKOUT ANALYSIS
    print("🚩 FLAG BREAKOUT CRITERIA:")
    
    # 1. Prior Impulse Analysis
    print("  1. Prior Impulse (Required: ≥30%):")
    impulse_detected = False
    best_impulse = 0
    impulse_window = None
    
    for i in range(20, len(bars) - 20):
        window_high = np.max(highs[i-20:i+20])
        window_low = np.min(lows[i-20:i+20])
        if window_high > window_low:
            move_pct = (window_high - window_low) / window_low * 100
            if move_pct > best_impulse:
                best_impulse = move_pct
                impulse_window = f"Days {i-20} to {i+20}"
            if move_pct >= 30:
                impulse_detected = True
                break
    
    impulse_status = "✅ PASS" if impulse_detected else "❌ FAIL"
    print(f"     Result: {impulse_status}")
    print(f"     Best Impulse: {best_impulse:.1f}%")
    print(f"     Window: {impulse_window}")
    
    # 2. Higher Lows Analysis
    print("\n  2. Higher Lows Pattern (Required: ≥50% of last 20 days):")
    recent_lows = lows[-20:]
    higher_lows = 0
    lower_lows = 0
    equal_lows = 0
    
    for i in range(1, len(recent_lows)):
        if recent_lows[i] > recent_lows[i-1]:
            higher_lows += 1
        elif recent_lows[i] < recent_lows[i-1]:
            lower_lows += 1
        else:
            equal_lows += 1
    
    higher_lows_pct = (higher_lows / len(recent_lows)) * 100
    higher_lows_ok = higher_lows >= 10  # At least half should be higher lows
    higher_lows_status = "✅ PASS" if higher_lows_ok else "❌ FAIL"
    
    print(f"     Result: {higher_lows_status}")
    print(f"     Higher Lows: {higher_lows}/{len(recent_lows)} ({higher_lows_pct:.1f}%)")
    print(f"     Lower Lows: {lower_lows}/{len(recent_lows)}")
    print(f"     Equal Lows: {equal_lows}/{len(recent_lows)}")
    
    # Show recent lows pattern
    print(f"     Recent Lows Pattern: {recent_lows[-10:].tolist()}")
    
    # 3. ATR Contraction Analysis
    print("\n  3. ATR Contraction (Required: <1.0):")
    recent_closes = closes[-20:]
    recent_highs = highs[-20:]
    recent_lows = lows[-20:]
    
    atr_values = []
    for i in range(1, len(recent_closes)):
        tr = max(
            recent_highs[i] - recent_lows[i],
            abs(recent_highs[i] - recent_closes[i-1]),
            abs(recent_lows[i] - recent_closes[i-1])
        )
        atr_values.append(tr)
    
    recent_atr = np.mean(atr_values[-10:]) if len(atr_values) >= 10 else 0
    baseline_atr = np.mean(atr_values[:10]) if len(atr_values) >= 10 else 0
    atr_contraction = recent_atr / baseline_atr if baseline_atr > 0 else 1.0
    atr_contraction_ok = atr_contraction < 1.0
    atr_status = "✅ PASS" if atr_contraction_ok else "❌ FAIL"
    
    print(f"     Result: {atr_status}")
    print(f"     Recent ATR (last 10): {recent_atr:.4f}")
    print(f"     Baseline ATR (first 10): {baseline_atr:.4f}")
    print(f"     ATR Ratio: {atr_contraction:.3f}")
    print(f"     Interpretation: {'Contraction' if atr_contraction_ok else 'Expansion'}")
    
    # 4. Breakout Above Recent High
    print("\n  4. Breakout Above Recent High (Required: +1.5%):")
    recent_high = np.max(recent_highs)
    required_price = recent_high * 1.015
    breakout_distance = ((current_price - recent_high) / recent_high * 100) if recent_high > 0 else 0
    breakout_above_ok = current_price > required_price
    breakout_status = "✅ PASS" if breakout_above_ok else "❌ FAIL"
    
    print(f"     Result: {breakout_status}")
    print(f"     Recent High: ${recent_high:.2f}")
    print(f"     Required Price: ${required_price:.2f}")
    print(f"     Current Price: ${current_price:.2f}")
    print(f"     Distance: {breakout_distance:.2f}%")
    
    # Flag breakout overall
    flag_passed = impulse_detected and higher_lows_ok and atr_contraction_ok and breakout_above_ok
    flag_overall_status = "✅ FLAG BREAKOUT DETECTED" if flag_passed else "❌ NO FLAG BREAKOUT"
    print(f"\n  🚩 FLAG BREAKOUT RESULT: {flag_overall_status}")
    
    # RANGE BREAKOUT ANALYSIS
    print("\n📦 RANGE BREAKOUT CRITERIA:")
    
    # 1. Tight Base Analysis
    print("  1. Tight Base (Required: ≤15% range):")
    base_closes = closes[-30:]
    range_high = np.max(base_closes)
    range_low = np.min(base_closes)
    range_size = range_high - range_low
    range_pct = (range_size / range_low * 100) if range_low > 0 else 0
    tight_base_ok = range_pct <= 15.0
    tight_base_status = "✅ PASS" if tight_base_ok else "❌ FAIL"
    
    print(f"     Result: {tight_base_status}")
    print(f"     Range High: ${range_high:.2f}")
    print(f"     Range Low: ${range_low:.2f}")
    print(f"     Range Size: ${range_size:.2f}")
    print(f"     Range Percentage: {range_pct:.1f}%")
    print(f"     Interpretation: {'Tight' if tight_base_ok else 'Wide'}")
    
    # 2. ATR Contraction (Range version)
    print("\n  2. ATR Contraction (Required: ≤0.8):")
    def _atr(h, l, c, n=14):
        prev = np.roll(c, 1)
        prev[0] = c[0]
        tr = np.maximum.reduce([h - l, abs(h - prev), abs(l - prev)])
        return np.mean(tr[-n:])
    
    atr14 = _atr(highs, lows, closes, 14)
    atr50 = np.mean([_atr(highs[i-14:i], lows[i-14:i], closes[i-14:i])
                     for i in range(14, len(closes))][-50:]) if len(closes) > 63 else atr14
    atr_ratio = atr14 / atr50 if atr50 > 0 else 1.0
    range_atr_ok = atr_ratio <= 0.8
    range_atr_status = "✅ PASS" if range_atr_ok else "❌ FAIL"
    
    print(f"     Result: {range_atr_status}")
    print(f"     ATR 14-day: {atr14:.4f}")
    print(f"     ATR 50-day: {atr50:.4f}")
    print(f"     ATR Ratio: {atr_ratio:.3f}")
    print(f"     Interpretation: {'Contraction' if range_atr_ok else 'Expansion'}")
    
    # 3. Volume Expansion Analysis
    print("\n  3. Volume Expansion (Required: ≥1.5x):")
    vol50 = np.mean(volumes[-51:-1]) if len(volumes) > 50 else np.mean(volumes)
    vol_mult = current_volume / vol50 if vol50 > 0 else 1
    vol_spike_ok = vol_mult >= 1.5
    vol_status = "✅ PASS" if vol_spike_ok else "❌ FAIL"
    
    print(f"     Result: {vol_status}")
    print(f"     Current Volume: {current_volume:,.0f}")
    print(f"     Average Volume (50-day): {vol50:,.0f}")
    print(f"     Volume Multiple: {vol_mult:.1f}x")
    print(f"     Interpretation: {'High Volume' if vol_spike_ok else 'Normal Volume'}")
    
    # 4. Price Breakout Analysis
    print("\n  4. Price Breakout (Required: +1.5% above range high):")
    min_break_price = range_high * 1.015
    price_break_ok = current_price >= min_break_price
    price_break_status = "✅ PASS" if price_break_ok else "❌ FAIL"
    price_distance = ((current_price - range_high) / range_high * 100) if range_high > 0 else 0
    
    print(f"     Result: {price_break_status}")
    print(f"     Range High: ${range_high:.2f}")
    print(f"     Required Break Price: ${min_break_price:.2f}")
    print(f"     Current Price: ${current_price:.2f}")
    print(f"     Distance Above Range: {price_distance:.2f}%")
    
    # Range breakout overall
    range_passed = tight_base_ok and range_atr_ok and vol_spike_ok and price_break_ok
    range_overall_status = "✅ RANGE BREAKOUT DETECTED" if range_passed else "❌ NO RANGE BREAKOUT"
    print(f"\n  📦 RANGE BREAKOUT RESULT: {range_overall_status}")
    
    # Overall result
    any_breakout = flag_passed or range_passed
    print(f"\n🎯 OVERALL RESULT: {'🎯 BREAKOUT SIGNAL DETECTED!' if any_breakout else '🚫 No breakout signal detected'}")
    
    # Additional context
    print(f"\n📊 ADDITIONAL CONTEXT:")
    print(f"  • Price vs 20-day SMA: {((current_price / np.mean(closes[-20:]) - 1) * 100):+.1f}%")
    print(f"  • Price vs 50-day SMA: {((current_price / np.mean(closes[-50:]) - 1) * 100):+.1f}%")
    print(f"  • Recent 5-day Performance: {((current_price / closes[-5] - 1) * 100):+.1f}%")
    print(f"  • Recent 10-day Performance: {((current_price / closes[-10] - 1) * 100):+.1f}%")

def main():
    """Main analysis function"""
    print("🔍 PRTS July 2020 - Early Days Detailed Analysis")
    print("Analyzing July 1, 2, 6, 7, and 8 in detail")
    
    try:
        # Get data
        bars = get_july_data()
        print(f"📊 Fetched {len(bars)} total bars")
        
        # Analyze specific days
        target_dates = ["2020-07-01", "2020-07-02", "2020-07-06", "2020-07-07", "2020-07-08"]
        analyze_specific_days(bars, target_dates)
        
        print("\n" + "=" * 90)
        print("📋 EARLY DAYS SUMMARY:")
        print("=" * 90)
        print("🔍 Detailed analysis of July 1, 2, 6, 7, and 8")
        print("📊 These were the consolidation days and the first big move")
        print("🎯 Shows exactly why no breakouts were detected")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
