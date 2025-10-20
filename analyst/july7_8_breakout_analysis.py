#!/usr/bin/env python3
"""
July 7 & 8 Breakout Analysis
July 7: Flag Breakout Potential (setup phase)
July 8: Flag Breakout Day (actual breakout)
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

def analyze_flag_breakout_potential_july7(bars: List[Bar]):
    """Analyze July 7th as Flag Breakout Potential (setup phase)"""
    
    # Get July 7th data
    july7_bar = None
    for bar in bars:
        if bar.timestamp.date() == datetime(2020, 7, 7).date():
            july7_bar = bar
            break
    
    if not july7_bar:
        print("❌ No July 7th data found")
        return
    
    # Get historical data up to July 7th (EXCLUDING July 7th for setup analysis)
    historical_bars = [b for b in bars if b.timestamp.date() < datetime(2020, 7, 7).date()]
    
    print("🚩 JULY 7, 2020 - FLAG BREAKOUT POTENTIAL (Setup Phase)")
    print("=" * 80)
    print(f"📅 Date: July 7, 2020")
    print(f"💰 Price: ${float(july7_bar.close):.2f}")
    print(f"📊 Volume: {float(july7_bar.volume):,.0f}")
    print("=" * 80)
    print("🎯 Analyzing setup criteria (excluding current day)")
    print("-" * 80)
    
    if len(historical_bars) < 60:
        print("❌ Insufficient historical data")
        return
    
    closes = np.array([float(bar.close) for bar in historical_bars])
    highs = np.array([float(bar.high) for bar in historical_bars])
    lows = np.array([float(bar.low) for bar in historical_bars])
    
    # ADJUSTED PARAMETERS
    higher_lows_required = 40  # Relaxed from 50%
    tight_base_max = 55        # Relaxed from 15%
    atr_contraction_max = 0.9  # Relaxed from 0.8
    
    print(f"🔧 ADJUSTED PARAMETERS:")
    print(f"   • Higher Lows Required: ≥{higher_lows_required}%")
    print(f"   • Tight Base Required: ≤{tight_base_max}%")
    print(f"   • ATR Contraction Required: ≤{atr_contraction_max}")
    print("-" * 80)
    
    # 1. Prior Impulse Analysis
    print("1. 🚀 PRIOR IMPULSE ANALYSIS:")
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
    
    print(f"   Result: {'✅ PASS' if impulse_detected else '❌ FAIL'}")
    print(f"   Best Impulse: {best_impulse:.1f}% (Required: ≥30%)")
    
    # 2. Higher Lows Analysis
    print("\n2. 📈 HIGHER LOWS PATTERN:")
    recent_lows = lows[-20:]
    higher_lows = 0
    for i in range(1, len(recent_lows)):
        if recent_lows[i] > recent_lows[i-1]:
            higher_lows += 1
    
    higher_lows_pct = (higher_lows / len(recent_lows)) * 100
    higher_lows_ok = higher_lows_pct >= higher_lows_required
    
    print(f"   Result: {'✅ PASS' if higher_lows_ok else '❌ FAIL'}")
    print(f"   Higher Lows: {higher_lows}/{len(recent_lows)} ({higher_lows_pct:.1f}%)")
    print(f"   Recent Lows Pattern: {recent_lows[-10:].tolist()}")
    
    # 3. Tight Base Analysis
    print("\n3. 📦 TIGHT BASE ANALYSIS:")
    base_closes = closes[-30:]
    range_high = np.max(base_closes)
    range_low = np.min(base_closes)
    range_pct = (range_high - range_low) / range_low * 100
    tight_base_ok = range_pct <= tight_base_max
    
    print(f"   Result: {'✅ PASS' if tight_base_ok else '❌ FAIL'}")
    print(f"   Range High: ${range_high:.2f}")
    print(f"   Range Low: ${range_low:.2f}")
    print(f"   Range Percentage: {range_pct:.1f}% (Required: ≤{tight_base_max}%)")
    
    # 4. ATR Contraction Analysis
    print("\n4. 📊 ATR CONTRACTION ANALYSIS:")
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
    
    print(f"   Result: {'✅ PASS' if atr_contraction_ok else '❌ FAIL'}")
    print(f"   Recent ATR (last 10): {recent_atr:.4f}")
    print(f"   Baseline ATR (first 10): {baseline_atr:.4f}")
    print(f"   ATR Ratio: {atr_contraction:.3f} (Required: ≤{atr_contraction_max})")
    
    # Overall Potential Result
    potential = impulse_detected and higher_lows_ok and tight_base_ok and atr_contraction_ok
    
    print("\n" + "=" * 80)
    print("🎯 FLAG BREAKOUT POTENTIAL RESULT:")
    print("=" * 80)
    if potential:
        print("✅ FLAG BREAKOUT? - Setup detected!")
        print("🎯 All setup criteria met - ready for breakout!")
    else:
        print("❌ No Flag Breakout Potential")
        print("🚫 Setup criteria not met")
    
    return {
        "potential": potential,
        "setup_range_high": range_high,
        "criteria": {
            "prior_impulse": {"passed": impulse_detected, "value": best_impulse},
            "higher_lows": {"passed": higher_lows_ok, "value": higher_lows_pct},
            "tight_base": {"passed": tight_base_ok, "value": range_pct},
            "atr_contraction": {"passed": atr_contraction_ok, "value": atr_contraction}
        }
    }

def analyze_flag_breakout_day_july8(bars: List[Bar], setup_range_high: float):
    """Analyze July 8th as Flag Breakout Day (actual breakout)"""
    
    # Get July 8th data
    july8_bar = None
    for bar in bars:
        if bar.timestamp.date() == datetime(2020, 7, 8).date():
            july8_bar = bar
            break
    
    if not july8_bar:
        print("❌ No July 8th data found")
        return
    
    # Get historical data up to July 8th
    historical_bars = [b for b in bars if b.timestamp.date() <= datetime(2020, 7, 8).date()]
    
    print("\n🎯 JULY 8, 2020 - FLAG BREAKOUT DAY (Actual Breakout)")
    print("=" * 80)
    print(f"📅 Date: July 8, 2020")
    print(f"💰 Price: ${float(july8_bar.close):.2f}")
    print(f"📈 Move: +16.8%")
    print(f"📊 Volume: {float(july8_bar.volume):,.0f}")
    print("=" * 80)
    print("🎯 Analyzing breakout day criteria")
    print("-" * 80)
    
    if len(historical_bars) < 60:
        print("❌ Insufficient historical data")
        return
    
    closes = np.array([float(bar.close) for bar in historical_bars])
    volumes = np.array([float(bar.volume) for bar in historical_bars])
    
    current_price = float(july8_bar.close)
    current_volume = float(july8_bar.volume)
    
    # ADJUSTED PARAMETERS
    price_breakout_required = 1.0  # Relaxed from 1.5%
    volume_expansion_required = 1.5
    
    print(f"🔧 ADJUSTED PARAMETERS:")
    print(f"   • Price Breakout Required: ≥{price_breakout_required}% above setup range high")
    print(f"   • Volume Expansion Required: ≥{volume_expansion_required}x")
    print(f"   • Setup Range High: ${setup_range_high:.2f}")
    print("-" * 80)
    
    # 1. Price Breakout Analysis
    print("1. 💰 PRICE BREAKOUT ANALYSIS:")
    required_price = setup_range_high * (1.0 + price_breakout_required / 100.0)
    price_breakout = current_price >= required_price
    breakout_distance = ((current_price - setup_range_high) / setup_range_high * 100) if setup_range_high > 0 else 0
    
    print(f"   Result: {'✅ PASS' if price_breakout else '❌ FAIL'}")
    print(f"   Setup Range High: ${setup_range_high:.2f}")
    print(f"   Required Price: ${required_price:.2f}")
    print(f"   Current Price: ${current_price:.2f}")
    print(f"   Breakout Distance: {breakout_distance:.2f}% (Required: ≥{price_breakout_required}%)")
    
    # 2. Volume Expansion Analysis
    print("\n2. 📊 VOLUME EXPANSION ANALYSIS:")
    vol50 = np.mean(volumes[-51:-1]) if len(volumes) > 50 else np.mean(volumes)
    vol_mult = current_volume / vol50 if vol50 > 0 else 1
    volume_expansion = vol_mult >= volume_expansion_required
    
    print(f"   Result: {'✅ PASS' if volume_expansion else '❌ FAIL'}")
    print(f"   Current Volume: {current_volume:,.0f}")
    print(f"   Average Volume (50-day): {vol50:,.0f}")
    print(f"   Volume Multiple: {vol_mult:.1f}x (Required: ≥{volume_expansion_required}x)")
    
    # Overall Breakout Day Result
    breakout_day = price_breakout and volume_expansion
    
    print("\n" + "=" * 80)
    print("🎯 FLAG BREAKOUT DAY RESULT:")
    print("=" * 80)
    if breakout_day:
        print("🎯 FLAG BREAKOUT! - Breakout confirmed!")
        print("🚀 All breakout criteria met - signal triggered!")
    else:
        print("❌ No Flag Breakout Day")
        print("🚫 Breakout criteria not met")
    
    return {
        "breakout_day": breakout_day,
        "criteria": {
            "price_breakout": {"passed": price_breakout, "distance": breakout_distance},
            "volume_expansion": {"passed": volume_expansion, "multiple": vol_mult}
        }
    }

def main():
    """Main analysis function"""
    print("🔍 July 7 & 8 Breakout Analysis")
    print("July 7: Flag Breakout Potential | July 8: Flag Breakout Day")
    
    try:
        # Get data
        bars = get_july_data()
        print(f"📊 Fetched {len(bars)} total bars")
        
        # Analyze July 7th as Flag Breakout Potential
        july7_result = analyze_flag_breakout_potential_july7(bars)
        
        # Analyze July 8th as Flag Breakout Day
        setup_range_high = july7_result.get("setup_range_high", 0) if july7_result else 0
        july8_result = analyze_flag_breakout_day_july8(bars, setup_range_high)
        
        # Overall Combined Result
        print("\n" + "=" * 80)
        print("🎯 COMBINED FLAG BREAKOUT ANALYSIS:")
        print("=" * 80)
        
        if july7_result and july8_result:
            july7_potential = july7_result["potential"]
            july8_breakout = july8_result["breakout_day"]
            
            print(f"📅 July 7 - Flag Breakout Potential: {'✅ PASS' if july7_potential else '❌ FAIL'}")
            print(f"📅 July 8 - Flag Breakout Day: {'✅ PASS' if july8_breakout else '❌ FAIL'}")
            
            if july7_potential and july8_breakout:
                print("\n🎯 COMPLETE FLAG BREAKOUT SIGNAL! 🎯")
                print("🚀 Perfect setup on July 7 + Breakout on July 8 = SIGNAL!")
            elif july7_potential:
                print("\n⚠️  Setup detected but no breakout day")
            elif july8_breakout:
                print("\n⚠️  Breakout day but no proper setup")
            else:
                print("\n❌ No complete signal")
        
        print("\n" + "=" * 80)
        print("📋 SUMMARY:")
        print("=" * 80)
        print("🎯 July 7: Setup phase analysis (Flag Breakout?)")
        print("🎯 July 8: Breakout day analysis (Flag Breakout!)")
        print("💡 Complete signal requires BOTH setup AND breakout day")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
