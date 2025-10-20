#!/usr/bin/env python3
"""
Tight Base Analysis - 20 Trading Days with 40% Threshold
Updated parameters: 20-day timeframe, 40% threshold
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

def analyze_flag_breakout_potential_20day_40pct(bars: List[Bar], target_date, current_price: float, current_volume: float) -> Dict:
    """Analyze Flag Breakout Potential using 20-day timeframe and 40% threshold"""
    
    # Get historical data up to target date (EXCLUDING target date for setup analysis)
    historical_bars = [b for b in bars if b.timestamp.date() < target_date]
    
    if len(historical_bars) < 60:
        return {"potential": False, "reason": "Insufficient data"}
    
    closes = np.array([float(bar.close) for bar in historical_bars])
    highs = np.array([float(bar.high) for bar in historical_bars])
    lows = np.array([float(bar.low) for bar in historical_bars])
    
    # UPDATED PARAMETERS
    higher_lows_required = 40  # Relaxed from 50%
    tight_base_max = 40        # NEW: 40% threshold with 20-day timeframe
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
    base_closes = closes[-20:]  # Trade-off: Use 20-day timeframe
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

def analyze_july_days_20day_40pct(bars: List[Bar]):
    """Analyze July days for Flag Breakout Potential with new parameters"""
    
    # Target dates
    target_dates = [
        datetime(2020, 7, 1).date(),
        datetime(2020, 7, 2).date(),
        datetime(2020, 7, 6).date(),
        datetime(2020, 7, 7).date(),
        datetime(2020, 7, 8).date()
    ]
    
    print("🚩 JULY DAYS - FLAG BREAKOUT POTENTIAL ANALYSIS")
    print("=" * 80)
    print("🔧 UPDATED PARAMETERS:")
    print("   • Higher Lows Required: ≥40%")
    print("   • Tight Base Required: ≤40% (20-day timeframe)")
    print("   • ATR Contraction Required: ≤0.9")
    print("=" * 80)
    
    results = []
    
    for target_date in target_dates:
        # Get the bar for this date
        target_bar = None
        for bar in bars:
            if bar.timestamp.date() == target_date:
                target_bar = bar
                break
        
        if not target_bar:
            print(f"❌ No data found for {target_date}")
            continue
        
        price = float(target_bar.close)
        volume = float(target_bar.volume)
        
        print(f"\n📅 {target_date} - ${price:.2f} | Vol: {volume:,.0f}")
        print("-" * 70)
        
        # Analyze Flag Breakout Potential
        result = analyze_flag_breakout_potential_20day_40pct(bars, target_date, price, volume)
        
        if result["potential"]:
            print("  ✅ FLAG BREAKOUT? - Setup detected!")
            criteria = result["criteria"]
            print(f"    • Prior Impulse: {criteria['prior_impulse']['best_impulse']:.1f}% ✅")
            print(f"    • Higher Lows: {criteria['higher_lows']['percentage']:.1f}% ✅")
            print(f"    • Tight Base: {criteria['tight_base']['range_pct']:.1f}% ✅")
            print(f"    • ATR Contraction: {criteria['atr_contraction']['ratio']:.3f} ✅")
        else:
            print("  ❌ No Flag Breakout Potential")
            criteria = result["criteria"]
            print(f"    • Prior Impulse: {criteria['prior_impulse']['best_impulse']:.1f}% {'✅' if criteria['prior_impulse']['passed'] else '❌'}")
            print(f"    • Higher Lows: {criteria['higher_lows']['percentage']:.1f}% {'✅' if criteria['higher_lows']['passed'] else '❌'}")
            print(f"    • Tight Base: {criteria['tight_base']['range_pct']:.1f}% {'✅' if criteria['tight_base']['passed'] else '❌'}")
            print(f"    • ATR Contraction: {criteria['atr_contraction']['ratio']:.3f} {'✅' if criteria['atr_contraction']['passed'] else '❌'}")
            
            # Show which criteria failed
            failed_criteria = []
            if not criteria['prior_impulse']['passed']:
                failed_criteria.append("Prior Impulse")
            if not criteria['higher_lows']['passed']:
                failed_criteria.append("Higher Lows")
            if not criteria['tight_base']['passed']:
                failed_criteria.append("Tight Base")
            if not criteria['atr_contraction']['passed']:
                failed_criteria.append("ATR Contraction")
            
            if failed_criteria:
                print(f"    🚫 Failed: {', '.join(failed_criteria)}")
        
        results.append({
            "date": target_date,
            "potential": result["potential"],
            "tight_base_pct": result["criteria"]["tight_base"]["range_pct"]
        })
    
    # Summary table
    print(f"\n📊 SUMMARY TABLE:")
    print("=" * 80)
    print(f"{'Date':<12} | {'Tight Base %':<12} | {'Result':<20}")
    print("=" * 80)
    for result in results:
        status = "✅ FLAG BREAKOUT?" if result["potential"] else "❌ No Potential"
        print(f"{result['date']} | {result['tight_base_pct']:>10.1f}% | {status:<20}")
    print("=" * 80)
    
    # Count results
    passed_count = sum(1 for r in results if r["potential"])
    total_count = len(results)
    
    print(f"\n📈 RESULTS SUMMARY:")
    print(f"   • Total days analyzed: {total_count}")
    print(f"   • Days with Flag Breakout Potential: {passed_count}")
    print(f"   • Success rate: {passed_count/total_count*100:.1f}%")
    
    return results

def main():
    """Main analysis function"""
    print("🔍 July Days Analysis - 20-Day Timeframe, 40% Threshold")
    print("Updated parameters for better sensitivity")
    
    try:
        # Get data
        bars = get_july_data()
        print(f"📊 Fetched {len(bars)} total bars")
        
        # Analyze July days with new parameters
        results = analyze_july_days_20day_40pct(bars)
        
        print("\n" + "=" * 80)
        print("📋 FINAL SUMMARY:")
        print("=" * 80)
        print("🎯 Updated Parameters:")
        print("   • Tight Base: 20-day timeframe, ≤40% threshold")
        print("   • Higher Lows: ≥40%")
        print("   • ATR Contraction: ≤0.9")
        print("💡 More sensitive parameters catch more potential setups")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
