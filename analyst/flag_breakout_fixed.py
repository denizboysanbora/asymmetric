#!/usr/bin/env python3
"""
Fixed Flag Breakout Analysis - Exclude breakout day from setup calculations
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
    
    request = StockBarsRequest(
        symbol_or_symbols="PRTS",
        timeframe=TimeFrame.Day,
        start=datetime(2020, 1, 1),
        end=datetime(2020, 7, 31)
    )
    
    bars = client.get_stock_bars(request)
    return bars.data["PRTS"]

def detect_flag_breakout_potential(bars: List[Bar], current_date, current_price: float) -> Dict:
    """
    Detect Flag Breakout Potential (setup phase)
    EXCLUDE the current breakout day from setup calculations
    """
    if len(bars) < 60:
        return {"potential": False, "reason": "Insufficient data"}
    
    # EXCLUDE current day from setup analysis
    setup_bars = [bar for bar in bars if bar.timestamp.date() < current_date]
    
    if len(setup_bars) < 30:
        return {"potential": False, "reason": "Insufficient setup data"}
    
    closes = np.array([float(bar.close) for bar in setup_bars])
    highs = np.array([float(bar.high) for bar in setup_bars])
    lows = np.array([float(bar.low) for bar in setup_bars])
    
    # 1. Prior Impulse (30%+ move in last 60 days)
    impulse_detected = False
    best_impulse = 0
    
    for i in range(20, len(setup_bars) - 20):
        window_high = np.max(highs[i-20:i+20])
        window_low = np.min(lows[i-20:i+20])
        if window_high > window_low:
            move_pct = (window_high - window_low) / window_low * 100
            if move_pct > best_impulse:
                best_impulse = move_pct
            if move_pct >= 30:
                impulse_detected = True
                break
    
    # 2. Higher Lows Pattern (last 20 days of setup, excluding current day)
    recent_lows = lows[-20:]
    higher_lows = 0
    for i in range(1, len(recent_lows)):
        if recent_lows[i] > recent_lows[i-1]:
            higher_lows += 1
    
    higher_lows_pct = (higher_lows / len(recent_lows)) * 100
    higher_lows_ok = higher_lows_pct >= 40  # Relaxed from 50%
    
    # 3. Tight Base (last 30 days of setup, excluding current day)
    base_closes = closes[-30:]
    range_high = np.max(base_closes)
    range_low = np.min(base_closes)
    range_pct = (range_high - range_low) / range_low * 100
    tight_base_ok = range_pct <= 25  # Relaxed from 15%
    
    # 4. ATR Contraction (last 20 days of setup, excluding current day)
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
    atr_contraction_ok = atr_contraction <= 0.9  # Relaxed from 0.8
    
    # Overall potential
    potential = impulse_detected and higher_lows_ok and tight_base_ok and atr_contraction_ok
    
    return {
        "potential": potential,
        "criteria": {
            "prior_impulse": {
                "detected": impulse_detected,
                "best_impulse": best_impulse,
                "passed": impulse_detected
            },
            "higher_lows": {
                "count": higher_lows,
                "percentage": higher_lows_pct,
                "passed": higher_lows_ok
            },
            "tight_base": {
                "range_pct": range_pct,
                "range_high": range_high,
                "range_low": range_low,
                "passed": tight_base_ok
            },
            "atr_contraction": {
                "ratio": atr_contraction,
                "passed": atr_contraction_ok
            }
        }
    }

def detect_flag_breakout_day(bars: List[Bar], current_price: float, current_volume: float, setup_range_high: float) -> Dict:
    """
    Detect Flag Breakout Day (actual breakout)
    Use the setup range high for breakout confirmation
    """
    if len(bars) < 60:
        return {"breakout_day": False, "reason": "Insufficient data"}
    
    closes = np.array([float(bar.close) for bar in bars])
    volumes = np.array([float(bar.volume) for bar in bars])
    
    # 1. Price Breakout (above setup range high)
    required_price = setup_range_high * 1.01  # 1.0% above setup range high
    price_breakout = current_price >= required_price
    breakout_distance = ((current_price - setup_range_high) / setup_range_high * 100) if setup_range_high > 0 else 0
    
    # 2. Volume Expansion
    vol50 = np.mean(volumes[-51:-1]) if len(volumes) > 50 else np.mean(volumes)
    vol_mult = current_volume / vol50 if vol50 > 0 else 1
    volume_expansion = vol_mult >= 1.5
    
    # Overall breakout day
    breakout_day = price_breakout and volume_expansion
    
    return {
        "breakout_day": breakout_day,
        "criteria": {
            "price_breakout": {
                "setup_range_high": setup_range_high,
                "required_price": required_price,
                "current_price": current_price,
                "distance_pct": breakout_distance,
                "passed": price_breakout
            },
            "volume_expansion": {
                "current_volume": current_volume,
                "avg_volume_50": vol50,
                "multiple": vol_mult,
                "passed": volume_expansion
            }
        }
    }

def analyze_july_flag_breakouts_fixed(bars: List[Bar]):
    """Analyze July days for fixed flag breakout detection"""
    
    # Get July bars
    july_bars = [bar for bar in bars if bar.timestamp.month == 7 and bar.timestamp.year == 2020]
    july_bars.sort(key=lambda x: x.timestamp.date())
    
    print("📊 FIXED FLAG BREAKOUT ANALYSIS - JULY 2020")
    print("=" * 80)
    print("🎯 Flag Breakout Potential: Setup phase (EXCLUDING current day)")
    print("🎯 Flag Breakout Day: Actual breakout (using setup range high)")
    print("=" * 80)
    
    for i, bar in enumerate(july_bars):
        date = bar.timestamp.date()
        price = float(bar.close)
        volume = float(bar.volume)
        
        # Get historical data up to this point
        historical_bars = [b for b in bars if b.timestamp.date() <= date]
        
        if len(historical_bars) < 60:
            continue
        
        # Calculate daily change
        if i > 0:
            prev_price = float(july_bars[i-1].close)
            daily_change = (price - prev_price) / prev_price * 100
        else:
            daily_change = 0.0
        
        print(f"\n📅 {date} - ${price:.2f} ({daily_change:+.1f}%) | Vol: {volume:,.0f}")
        print("-" * 70)
        
        # Check Flag Breakout Potential (setup phase - EXCLUDING current day)
        potential_result = detect_flag_breakout_potential(historical_bars, date, price)
        
        # Get setup range high for breakout day analysis
        setup_range_high = potential_result["criteria"]["tight_base"]["range_high"]
        
        # Check Flag Breakout Day (actual breakout)
        breakout_result = detect_flag_breakout_day(historical_bars, price, volume, setup_range_high)
        
        # Display results
        print("🚩 FLAG BREAKOUT POTENTIAL (Setup Phase - Excluding Current Day):")
        if potential_result["potential"]:
            print("  ✅ FLAG BREAKOUT? - Setup detected!")
            criteria = potential_result["criteria"]
            print(f"    • Prior Impulse: {criteria['prior_impulse']['best_impulse']:.1f}% ✅")
            print(f"    • Higher Lows: {criteria['higher_lows']['percentage']:.1f}% ✅")
            print(f"    • Tight Base: {criteria['tight_base']['range_pct']:.1f}% ✅")
            print(f"    • ATR Contraction: {criteria['atr_contraction']['ratio']:.3f} ✅")
        else:
            print("  ❌ No Flag Breakout Potential")
            criteria = potential_result["criteria"]
            print(f"    • Prior Impulse: {criteria['prior_impulse']['best_impulse']:.1f}% {'✅' if criteria['prior_impulse']['passed'] else '❌'}")
            print(f"    • Higher Lows: {criteria['higher_lows']['percentage']:.1f}% {'✅' if criteria['higher_lows']['passed'] else '❌'}")
            print(f"    • Tight Base: {criteria['tight_base']['range_pct']:.1f}% {'✅' if criteria['tight_base']['passed'] else '❌'}")
            print(f"    • ATR Contraction: {criteria['atr_contraction']['ratio']:.3f} {'✅' if criteria['atr_contraction']['passed'] else '❌'}")
        
        print("\n🎯 FLAG BREAKOUT DAY (Actual Breakout):")
        if breakout_result["breakout_day"]:
            print("  🎯 FLAG BREAKOUT! - Breakout confirmed!")
            criteria = breakout_result["criteria"]
            print(f"    • Price Breakout: ${price:.2f} vs ${criteria['price_breakout']['required_price']:.2f} ✅")
            print(f"    • Volume Expansion: {criteria['volume_expansion']['multiple']:.1f}x ✅")
        else:
            print("  ❌ No Flag Breakout Day")
            criteria = breakout_result["criteria"]
            print(f"    • Price Breakout: ${price:.2f} vs ${criteria['price_breakout']['required_price']:.2f} {'✅' if criteria['price_breakout']['passed'] else '❌'}")
            print(f"    • Volume Expansion: {criteria['volume_expansion']['multiple']:.1f}x {'✅' if criteria['volume_expansion']['passed'] else '❌'}")
        
        # Overall signal
        if potential_result["potential"] and breakout_result["breakout_day"]:
            print("\n🎯 COMPLETE FLAG BREAKOUT SIGNAL! 🎯")
        elif potential_result["potential"]:
            print("\n⚠️  Flag Breakout Potential only (setup phase)")
        elif breakout_result["breakout_day"]:
            print("\n⚠️  Breakout Day only (no proper setup)")

def main():
    """Main analysis function"""
    print("🔍 Fixed Flag Breakout Analysis")
    print("Excluding breakout day from setup calculations")
    
    try:
        # Get data
        bars = get_july_data()
        print(f"📊 Fetched {len(bars)} total bars")
        
        # Analyze fixed flag breakouts
        analyze_july_flag_breakouts_fixed(bars)
        
        print("\n" + "=" * 80)
        print("📋 FIXED BREAKOUT SUMMARY:")
        print("=" * 80)
        print("🎯 Flag Breakout Potential: Setup phase (excluding current day)")
        print("    • Prior impulse ≥30%")
        print("    • Higher lows ≥40% (relaxed)")
        print("    • Tight base ≤25% (relaxed, excluding breakout day)")
        print("    • ATR contraction ≤0.9 (relaxed)")
        print("\n🎯 Flag Breakout Day: Actual breakout criteria")
        print("    • Price breakout ≥1.0% above setup range high")
        print("    • Volume expansion ≥1.5x")
        print("\n💡 Complete signal requires BOTH potential AND breakout day")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
