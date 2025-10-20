#!/usr/bin/env python3
"""
AMD December 2019 Analysis - First Two Weeks
Using optimized flag breakout parameters: 20-day timeframe, 40% threshold
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

def get_amd_data():
    """Get AMD data for December 2019"""
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    client = StockHistoricalDataClient(api_key, secret_key)
    
    # Get extended data for analysis (starting from August 2019 to ensure enough history)
    request = StockBarsRequest(
        symbol_or_symbols="AMD",
        timeframe=TimeFrame.Day,
        start=datetime(2019, 8, 1),
        end=datetime(2019, 12, 31)
    )
    
    bars = client.get_stock_bars(request)
    return bars.data["AMD"]

def analyze_flag_breakout_potential(bars: List[Bar], target_date, current_price: float, current_volume: float) -> Dict:
    """Analyze Flag Breakout Potential using optimized parameters"""
    
    # Get historical data up to target date (EXCLUDING target date for setup analysis)
    historical_bars = [b for b in bars if b.timestamp.date() < target_date]
    
    if len(historical_bars) < 60:
        return {"potential": False, "reason": "Insufficient data"}
    
    closes = np.array([float(bar.close) for bar in historical_bars])
    highs = np.array([float(bar.high) for bar in historical_bars])
    lows = np.array([float(bar.low) for bar in historical_bars])
    
    # OPTIMIZED PARAMETERS (from PRTS analysis)
    higher_lows_required = 40  # Relaxed from 50%
    tight_base_max = 40        # 40% threshold with 20-day timeframe
    atr_contraction_max = 0.9  # Relaxed from 0.8
    
    # 1. Prior Impulse Analysis
    impulse_detected = False
    best_impulse = 0
    
    for i in range(20, len(historical_bars) - 20):
        window_high = np.max(highs[i-20:i+20])
        window_low = np.min(lows[i-20:i+20])
        if window_high > window_low:
            move_pct = (window_high - window_low) / window_low * 100
            if move_pct > best_impulse:
                best_impulse = move_pct
            if move_pct >= 30:
                impulse_detected = True
                break
    
    # 2. Higher Lows Analysis
    recent_lows = lows[-20:]
    higher_lows = 0
    for i in range(1, len(recent_lows)):
        if recent_lows[i] > recent_lows[i-1]:
            higher_lows += 1
    
    higher_lows_pct = (higher_lows / len(recent_lows)) * 100
    higher_lows_ok = higher_lows_pct >= higher_lows_required
    
    # 3. Tight Base Analysis (20-day timeframe)
    base_closes = closes[-20:]
    range_high = np.max(base_closes)
    range_low = np.min(base_closes)
    range_pct = (range_high - range_low) / range_low * 100
    tight_base_ok = range_pct <= tight_base_max
    
    # 4. ATR Contraction Analysis
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
    atr_contraction_ok = atr_contraction <= atr_contraction_max
    
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

def analyze_flag_breakout_day(bars: List[Bar], target_date, current_price: float, current_volume: float, setup_range_high: float) -> Dict:
    """Analyze Flag Breakout Day using optimized parameters"""
    
    # Get historical data up to target date
    historical_bars = [b for b in bars if b.timestamp.date() <= target_date]
    
    if len(historical_bars) < 60:
        return {"breakout_day": False, "reason": "Insufficient data"}
    
    closes = np.array([float(bar.close) for bar in historical_bars])
    volumes = np.array([float(bar.volume) for bar in historical_bars])
    
    # OPTIMIZED PARAMETERS
    price_breakout_required = 1.0  # 1.0% above setup range high
    volume_expansion_required = 1.5  # 1.5x volume expansion
    
    # 1. Price Breakout Analysis
    required_price = setup_range_high * (1.0 + price_breakout_required / 100.0)
    price_breakout = current_price >= required_price
    breakout_distance = ((current_price - setup_range_high) / setup_range_high * 100) if setup_range_high > 0 else 0
    
    # 2. Volume Expansion Analysis
    vol50 = np.mean(volumes[-51:-1]) if len(volumes) > 50 else np.mean(volumes)
    vol_mult = current_volume / vol50 if vol50 > 0 else 1
    volume_expansion = vol_mult >= volume_expansion_required
    
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

def analyze_amd_december_2019(bars: List[Bar]):
    """Analyze AMD for first two weeks of December 2019"""
    
    # Get December 2019 bars
    dec_bars = [bar for bar in bars if bar.timestamp.month == 12 and bar.timestamp.year == 2019]
    dec_bars.sort(key=lambda x: x.timestamp.date())
    
    # First two weeks of December
    first_two_weeks = dec_bars[:10]  # Approximately first 10 trading days
    
    print("🚩 AMD DECEMBER 2019 - FIRST TWO WEEKS ANALYSIS")
    print("=" * 80)
    print("🔧 OPTIMIZED PARAMETERS (from PRTS analysis):")
    print("   • Higher Lows Required: ≥40%")
    print("   • Tight Base Required: ≤40% (20-day timeframe)")
    print("   • ATR Contraction Required: ≤0.9")
    print("   • Price Breakout Required: ≥1.0% above setup range high")
    print("   • Volume Expansion Required: ≥1.5x")
    print("=" * 80)
    
    results = []
    
    for i, bar in enumerate(first_two_weeks):
        date = bar.timestamp.date()
        price = float(bar.close)
        volume = float(bar.volume)
        
        # Calculate daily change
        if i > 0:
            prev_price = float(first_two_weeks[i-1].close)
            daily_change = (price - prev_price) / prev_price * 100
        else:
            daily_change = 0.0
        
        print(f"\n📅 {date} - ${price:.2f} ({daily_change:+.1f}%) | Vol: {volume:,.0f}")
        print("-" * 70)
        
        # Analyze Flag Breakout Potential
        potential_result = analyze_flag_breakout_potential(bars, date, price, volume)
        
        # Get setup range high for breakout day analysis
        setup_range_high = potential_result["criteria"]["tight_base"]["range_high"]
        
        # Analyze Flag Breakout Day
        breakout_result = analyze_flag_breakout_day(bars, date, price, volume, setup_range_high)
        
        # Display results
        print("🚩 FLAG BREAKOUT POTENTIAL (Setup Phase):")
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
        
        results.append({
            "date": date,
            "price": price,
            "daily_change": daily_change,
            "volume": volume,
            "potential": potential_result["potential"],
            "breakout_day": breakout_result["breakout_day"],
            "tight_base_pct": potential_result["criteria"]["tight_base"]["range_pct"]
        })
    
    # Summary table
    print(f"\n📊 SUMMARY TABLE:")
    print("=" * 100)
    print(f"{'Date':<12} | {'Price':<8} | {'Change':<8} | {'Volume':<12} | {'Potential':<12} | {'Breakout':<12}")
    print("=" * 100)
    for result in results:
        potential_status = "✅ YES" if result["potential"] else "❌ NO"
        breakout_status = "✅ YES" if result["breakout_day"] else "❌ NO"
        print(f"{result['date']} | ${result['price']:>6.2f} | {result['daily_change']:>+6.1f}% | {result['volume']:>10,} | {potential_status:<12} | {breakout_status:<12}")
    print("=" * 100)
    
    # Count results
    potential_count = sum(1 for r in results if r["potential"])
    breakout_count = sum(1 for r in results if r["breakout_day"])
    complete_signals = sum(1 for r in results if r["potential"] and r["breakout_day"])
    
    print(f"\n📈 RESULTS SUMMARY:")
    print(f"   • Total days analyzed: {len(results)}")
    print(f"   • Days with Flag Breakout Potential: {potential_count}")
    print(f"   • Days with Flag Breakout Day: {breakout_count}")
    print(f"   • Complete Flag Breakout Signals: {complete_signals}")
    
    return results

def main():
    """Main analysis function"""
    print("🔍 AMD December 2019 Analysis - First Two Weeks")
    print("Using optimized flag breakout parameters")
    
    try:
        # Get data
        bars = get_amd_data()
        print(f"📊 Fetched {len(bars)} total bars")
        
        # Analyze AMD December 2019
        results = analyze_amd_december_2019(bars)
        
        print("\n" + "=" * 80)
        print("📋 FINAL SUMMARY:")
        print("=" * 80)
        print("🎯 AMD December 2019 - First Two Weeks Analysis")
        print("🔧 Used optimized parameters from PRTS analysis")
        print("💡 Shows how the algorithm performs on different stocks")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
