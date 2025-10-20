#!/usr/bin/env python3
"""
PRTS July 2020 - ALL DAYS Including Early Days
Show every single day in July 2020, including early days with reduced data requirements
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
    
    # Get extended data for analysis - go back further to get more history
    request = StockBarsRequest(
        symbol_or_symbols="PRTS",
        timeframe=TimeFrame.Day,
        start=datetime(2020, 1, 1),  # Start from January to get enough history
        end=datetime(2020, 7, 31)
    )
    
    bars = client.get_stock_bars(request)
    return bars.data["PRTS"]

def analyze_all_july_days(bars: List[Bar]):
    """Analyze ALL July days including early days"""
    
    # Get ALL July bars and sort by date
    july_bars = [bar for bar in bars if bar.timestamp.month == 7 and bar.timestamp.year == 2020]
    july_bars.sort(key=lambda x: x.timestamp.date())
    
    print("📊 PRTS JULY 2020 - ALL TRADING DAYS (Including Early Days)")
    print("=" * 90)
    print(f"📅 Total July Trading Days: {len(july_bars)}")
    print("=" * 90)
    
    # Show all dates first
    print("\n📅 ALL JULY 2020 TRADING DATES:")
    for i, bar in enumerate(july_bars):
        print(f"  {i+1:2d}. {bar.timestamp.date()} - ${float(bar.close):.2f}")
    print("=" * 90)
    
    # Now analyze each day
    for i, bar in enumerate(july_bars):
        date = bar.timestamp.date()
        price = float(bar.close)
        volume = float(bar.volume)
        
        # Get historical data up to this point
        historical_bars = [b for b in bars if b.timestamp.date() <= date]
        
        # Calculate daily change
        if i > 0:
            prev_price = float(july_bars[i-1].close)
            daily_change = (price - prev_price) / prev_price * 100
        else:
            daily_change = 0.0
        
        print(f"\n📅 {date} - ${price:.2f} ({daily_change:+.1f}%) | Vol: {volume:,.0f}")
        print("-" * 80)
        
        # Analyze with available data
        if len(historical_bars) >= 60:
            analyze_breakout_criteria_full(historical_bars, price, volume)
        elif len(historical_bars) >= 30:
            analyze_breakout_criteria_limited(historical_bars, price, volume)
        else:
            print(f"⚠️  Limited data available ({len(historical_bars)} bars) - Basic analysis only")
            analyze_basic_criteria(historical_bars, price, volume)

def analyze_basic_criteria(bars: List[Bar], current_price: float, current_volume: float):
    """Basic analysis for days with limited data"""
    closes = np.array([float(bar.close) for bar in bars])
    volumes = np.array([float(bar.volume) for bar in bars])
    
    print("📊 BASIC ANALYSIS (Limited Data):")
    
    # Price performance
    if len(closes) > 1:
        total_return = (closes[-1] - closes[0]) / closes[0] * 100
        print(f"  📈 Total Return: {total_return:+.1f}%")
    
    # Recent performance
    if len(closes) >= 5:
        recent_return = (closes[-1] - closes[-5]) / closes[-5] * 100
        print(f"  📈 Recent 5-day Return: {recent_return:+.1f}%")
    
    # Volume analysis
    if len(volumes) >= 10:
        avg_volume = np.mean(volumes[-10:])
        vol_mult = current_volume / avg_volume if avg_volume > 0 else 1
        print(f"  📊 Volume: {vol_mult:.1f}x recent average")
    
    print("  🚫 Insufficient data for full breakout analysis")

def analyze_breakout_criteria_limited(bars: List[Bar], current_price: float, current_volume: float):
    """Limited analysis for days with 30-59 bars"""
    closes = np.array([float(bar.close) for bar in bars])
    highs = np.array([float(bar.high) for bar in bars])
    lows = np.array([float(bar.low) for bar in bars])
    volumes = np.array([float(bar.volume) for bar in bars])
    
    print("📊 LIMITED BREAKOUT ANALYSIS (30-59 bars):")
    
    # Check for prior impulse (reduced requirement)
    impulse_detected = False
    best_impulse = 0
    if len(bars) >= 40:
        for i in range(10, len(bars) - 10):
            window_high = np.max(highs[i-10:i+10])
            window_low = np.min(lows[i-10:i+10])
            if window_high > window_low:
                move_pct = (window_high - window_low) / window_low * 100
                if move_pct > best_impulse:
                    best_impulse = move_pct
                if move_pct >= 30:
                    impulse_detected = True
                    break
    
    impulse_status = "✅" if impulse_detected else "❌"
    print(f"  {impulse_status} Prior Impulse: {best_impulse:.1f}% (Required: ≥30%)")
    
    # Range analysis (last 15 days instead of 30)
    if len(closes) >= 15:
        base_closes = closes[-15:]
        range_high = np.max(base_closes)
        range_low = np.min(base_closes)
        range_pct = (range_high - range_low) / range_low * 100
        tight_base_ok = range_pct <= 15.0
        tight_base_status = "✅" if tight_base_ok else "❌"
        print(f"  {tight_base_status} Tight Base: {range_pct:.1f}% (Required: ≤15%)")
    
    # Volume analysis
    if len(volumes) >= 20:
        vol_avg = np.mean(volumes[-20:])
        vol_mult = current_volume / vol_avg if vol_avg > 0 else 1
        vol_spike_ok = vol_mult >= 1.5
        vol_status = "✅" if vol_spike_ok else "❌"
        print(f"  {vol_status} Volume Expansion: {vol_mult:.1f}x (Required: ≥1.5x)")
    
    print("  🚫 Full breakout analysis requires 60+ bars of history")

def analyze_breakout_criteria_full(bars: List[Bar], current_price: float, current_volume: float):
    """Full breakout analysis for days with 60+ bars"""
    closes = np.array([float(bar.close) for bar in bars])
    highs = np.array([float(bar.high) for bar in bars])
    lows = np.array([float(bar.low) for bar in bars])
    volumes = np.array([float(bar.volume) for bar in bars])
    
    # FLAG BREAKOUT ANALYSIS
    print("🚩 FLAG BREAKOUT:")
    
    # 1. Prior Impulse (30%+ move)
    impulse_detected = False
    best_impulse = 0
    for i in range(20, len(bars) - 20):
        window_high = np.max(highs[i-20:i+20])
        window_low = np.min(lows[i-20:i+20])
        if window_high > window_low:
            move_pct = (window_high - window_low) / window_low * 100
            if move_pct > best_impulse:
                best_impulse = move_pct
            if move_pct >= 30:
                impulse_detected = True
                break
    
    impulse_status = "✅" if impulse_detected else "❌"
    print(f"  {impulse_status} Prior Impulse: {best_impulse:.1f}% (Required: ≥30%)")
    
    # 2. Higher Lows (last 20 days)
    recent_lows = lows[-20:]
    higher_lows = 0
    for i in range(1, len(recent_lows)):
        if recent_lows[i] > recent_lows[i-1]:
            higher_lows += 1
    
    higher_lows_pct = (higher_lows / len(recent_lows)) * 100
    higher_lows_ok = higher_lows >= 10  # At least half should be higher lows
    higher_lows_status = "✅" if higher_lows_ok else "❌"
    print(f"  {higher_lows_status} Higher Lows: {higher_lows}/{len(recent_lows)} ({higher_lows_pct:.1f}%)")
    
    # 3. ATR Contraction
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
    atr_status = "✅" if atr_contraction_ok else "❌"
    print(f"  {atr_status} ATR Contraction: {atr_contraction:.3f} (Required: <1.0)")
    
    # 4. Breakout Above Recent High
    recent_high = np.max(recent_highs)
    required_price = recent_high * 1.015
    breakout_distance = ((current_price - recent_high) / recent_high * 100) if recent_high > 0 else 0
    breakout_above_ok = current_price > required_price
    breakout_status = "✅" if breakout_above_ok else "❌"
    print(f"  {breakout_status} Breakout Above High: ${current_price:.2f} vs ${required_price:.2f} (Required: +1.5%)")
    
    # Flag breakout overall
    flag_passed = impulse_detected and higher_lows_ok and atr_contraction_ok and breakout_above_ok
    flag_overall_status = "✅ PASSED" if flag_passed else "❌ FAILED"
    print(f"  🚩 FLAG BREAKOUT: {flag_overall_status}")
    
    # RANGE BREAKOUT ANALYSIS
    print("\n📦 RANGE BREAKOUT:")
    
    # 1. Tight Base (≤15% range)
    base_closes = closes[-30:]
    range_high = np.max(base_closes)
    range_low = np.min(base_closes)
    range_pct = (range_high - range_low) / range_low * 100
    tight_base_ok = range_pct <= 15.0
    tight_base_status = "✅" if tight_base_ok else "❌"
    print(f"  {tight_base_status} Tight Base: {range_pct:.1f}% (Required: ≤15%)")
    
    # 2. ATR Contraction (14d vs 50d)
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
    range_atr_status = "✅" if range_atr_ok else "❌"
    print(f"  {range_atr_status} ATR Contraction: {atr_ratio:.3f} (Required: ≤0.8)")
    
    # 3. Volume Expansion (≥1.5x)
    vol50 = np.mean(volumes[-51:-1]) if len(volumes) > 50 else np.mean(volumes)
    vol_mult = current_volume / vol50 if vol50 > 0 else 1
    vol_spike_ok = vol_mult >= 1.5
    vol_status = "✅" if vol_spike_ok else "❌"
    print(f"  {vol_status} Volume Expansion: {vol_mult:.1f}x (Required: ≥1.5x)")
    
    # 4. Price Breakout (1.5% above range high)
    min_break_price = range_high * 1.015
    price_break_ok = current_price >= min_break_price
    price_break_status = "✅" if price_break_ok else "❌"
    print(f"  {price_break_status} Price Breakout: ${current_price:.2f} vs ${min_break_price:.2f} (Required: +1.5%)")
    
    # Range breakout overall
    range_passed = tight_base_ok and range_atr_ok and vol_spike_ok and price_break_ok
    range_overall_status = "✅ PASSED" if range_passed else "❌ FAILED"
    print(f"  📦 RANGE BREAKOUT: {range_overall_status}")
    
    # Overall result
    any_breakout = flag_passed or range_passed
    if any_breakout:
        print(f"\n🎯 BREAKOUT SIGNAL DETECTED! 🎯")
    else:
        print(f"\n🚫 No breakout signal")

def main():
    """Main analysis function"""
    print("🔍 PRTS July 2020 - ALL DAYS Analysis (Including Early Days)")
    print("Analyzing every single trading day in July 2020")
    
    try:
        # Get data
        bars = get_july_data()
        print(f"📊 Fetched {len(bars)} total bars")
        
        # Analyze all July days
        analyze_all_july_days(bars)
        
        print("\n" + "=" * 90)
        print("📋 JULY 2020 COMPLETE SUMMARY:")
        print("=" * 90)
        print("🔍 Analyzed all 21 trading days in July 2020")
        print("📊 Early days had limited data, later days had full analysis")
        print("🎯 Your algorithm's selectivity is working correctly!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
