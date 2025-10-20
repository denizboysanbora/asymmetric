#!/usr/bin/env python3
"""
PRTS July 2020 Complete Analysis - All Trading Days
Show every single day with detailed breakout criteria analysis
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import json

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

# Import breakout analysis functions
sys.path.insert(0, str(Path(__file__).parent))
from breakout.breakout_scanner import (
    detect_flag_breakout_setup, 
    detect_range_breakout_setup,
    calculate_rsi,
    calculate_atr,
    calculate_z_score
)

def analyze_complete_july(bars: List[Bar]) -> Dict:
    """Complete July analysis with all trading days"""
    
    # Filter for July 2020 bars
    july_bars = [bar for bar in bars if bar.timestamp.month == 7 and bar.timestamp.year == 2020]
    
    results = {
        "symbol": "PRTS",
        "month": "July 2020",
        "total_days": len(july_bars),
        "daily_analysis": []
    }
    
    print(f"📊 Found {len(july_bars)} July trading days")
    
    # Analyze each July day
    for i, current_bar in enumerate(july_bars):
        current_date = current_bar.timestamp.date()
        
        # Get all bars up to this point (need history for analysis)
        historical_bars = [bar for bar in bars if bar.timestamp.date() <= current_date]
        
        if len(historical_bars) < 60:  # Need at least 60 days of history
            continue
        
        # Calculate technical indicators
        closes = [float(bar.close) for bar in historical_bars]
        highs = [float(bar.high) for bar in historical_bars]
        lows = [float(bar.low) for bar in historical_bars]
        volumes = [float(bar.volume) for bar in historical_bars]
        
        rsi = calculate_rsi(closes)
        atr = calculate_atr(highs, lows, closes)
        z_score = calculate_z_score(closes)
        
        # Calculate daily change
        if len(closes) >= 2:
            daily_change = (closes[-1] - closes[-2]) / closes[-2] * 100
        else:
            daily_change = 0.0
        
        # Check flag breakout setup
        flag_breakout = detect_flag_breakout_setup(historical_bars, "PRTS")
        
        # Check range breakout setup
        range_breakout = detect_range_breakout_setup(historical_bars, "PRTS")
        
        # Detailed analysis of criteria
        analysis = analyze_breakout_criteria(historical_bars, current_date, closes[-1], daily_change, volumes[-1])
        
        results["daily_analysis"].append(analysis)
    
    return results

def analyze_breakout_criteria(bars: List[Bar], date, price: float, daily_change: float, volume: float) -> Dict:
    """Analyze all breakout criteria in detail"""
    if len(bars) < 60:
        return {"error": "Insufficient data"}
    
    closes = np.array([float(bar.close) for bar in bars])
    highs = np.array([float(bar.high) for bar in bars])
    lows = np.array([float(bar.low) for bar in bars])
    volumes = np.array([float(bar.volume) for bar in bars])
    
    # Calculate technical indicators
    rsi = calculate_rsi(closes.tolist())
    atr = calculate_atr(highs.tolist(), lows.tolist(), closes.tolist())
    z_score = calculate_z_score(closes.tolist())
    
    # FLAG BREAKOUT ANALYSIS
    flag_analysis = analyze_flag_detailed(closes, highs, lows)
    
    # RANGE BREAKOUT ANALYSIS
    range_analysis = analyze_range_detailed(closes, highs, lows, volumes, price)
    
    return {
        "date": date,
        "price": price,
        "daily_change_pct": daily_change,
        "volume": volume,
        "rsi": rsi,
        "atr": atr,
        "z_score": z_score,
        "flag_breakout": flag_analysis,
        "range_breakout": range_analysis
    }

def analyze_flag_detailed(closes, highs, lows):
    """Detailed flag breakout analysis"""
    # Check for prior impulse (30%+ move in last 60 days)
    impulse_detected = False
    impulse_pct = 0
    best_impulse = 0
    
    for i in range(20, len(closes) - 20):
        window_high = np.max(highs[i-20:i+20])
        window_low = np.min(lows[i-20:i+20])
        
        if window_high > window_low:
            move_pct = (window_high - window_low) / window_low
            if move_pct > best_impulse:
                best_impulse = move_pct
            if move_pct >= 0.30:  # 30%+ move
                impulse_detected = True
                impulse_pct = move_pct * 100
                break
    
    # Check for tight flag consolidation (last 20 days)
    recent_closes = closes[-20:]
    recent_highs = highs[-20:]
    recent_lows = lows[-20:]
    
    # Check for higher lows
    higher_lows = 0
    for i in range(1, len(recent_lows)):
        if recent_lows[i] > recent_lows[i-1]:
            higher_lows += 1
    
    # Check for ATR contraction
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
    
    # Check for breakout above recent high
    recent_high = np.max(recent_highs)
    current_price = recent_closes[-1]
    breakout_above_high = current_price > recent_high * 1.015  # 1.5% above recent high
    breakout_distance = ((current_price - recent_high) / recent_high * 100) if recent_high > 0 else 0
    
    return {
        "prior_impulse": {
            "detected": impulse_detected,
            "best_impulse_pct": best_impulse * 100,
            "required_impulse_pct": 30.0,
            "passed": impulse_detected
        },
        "higher_lows": {
            "count": higher_lows,
            "total_days": len(recent_lows),
            "percentage": (higher_lows / len(recent_lows)) * 100 if len(recent_lows) > 0 else 0,
            "passed": higher_lows >= 10  # At least half should be higher lows
        },
        "atr_contraction": {
            "recent_atr": recent_atr,
            "baseline_atr": baseline_atr,
            "ratio": atr_contraction,
            "required": "< 1.0",
            "passed": atr_contraction < 1.0
        },
        "breakout_above_high": {
            "recent_high": recent_high,
            "current_price": current_price,
            "required_price": recent_high * 1.015,
            "distance_pct": breakout_distance,
            "required_distance_pct": 1.5,
            "passed": breakout_above_high
        },
        "overall_passed": impulse_detected and higher_lows >= 10 and atr_contraction < 1.0 and breakout_above_high
    }

def analyze_range_detailed(closes, highs, lows, volumes, current_price):
    """Detailed range breakout analysis"""
    # Range tightness (last 30 bars)
    base_len = 30
    base_closes = closes[-base_len:]
    range_high = float(np.max(base_closes))
    range_low = float(np.min(base_closes))
    range_size = range_high - range_low
    range_pct = (range_size / range_low * 100) if range_low > 0 else 0
    tight_base = range_pct <= 15.0  # 15% threshold
    
    # ATR contraction (14d vs 50d)
    def _atr(h, l, c, n=14):
        prev = np.roll(c, 1)
        prev[0] = c[0]
        tr = np.maximum.reduce([h - l, abs(h - prev), abs(l - prev)])
        return np.mean(tr[-n:])
    
    atr14 = _atr(highs, lows, closes, 14)
    atr50 = np.mean([_atr(highs[i-14:i], lows[i-14:i], closes[i-14:i])
                     for i in range(14, len(closes))][-50:]) if len(closes) > 63 else atr14
    atr_ratio = atr14 / atr50 if atr50 > 0 else 1.0
    contraction_ok = atr_ratio <= 0.8
    
    # Volume expansion
    vol50 = np.mean(volumes[-51:-1]) if len(volumes) > 50 else np.mean(volumes)
    vol_mult = volumes[-1] / vol50 if vol50 > 0 else 1
    vol_spike = vol_mult >= 1.5
    
    # Breakout confirmation
    min_break_price = range_high * 1.015  # 1.5% above range high
    price_break = current_price >= min_break_price
    breakout_ok = price_break and vol_spike
    
    return {
        "tight_base": {
            "range_high": range_high,
            "range_low": range_low,
            "range_size": range_size,
            "range_pct": range_pct,
            "required_pct": 15.0,
            "passed": tight_base
        },
        "atr_contraction": {
            "atr14": atr14,
            "atr50": atr50,
            "ratio": atr_ratio,
            "required": "≤ 0.8",
            "passed": contraction_ok
        },
        "volume_expansion": {
            "current_volume": volumes[-1],
            "avg_volume_50": vol50,
            "multiple": vol_mult,
            "required": "≥ 1.5x",
            "passed": vol_spike
        },
        "price_breakout": {
            "min_break_price": min_break_price,
            "current_price": current_price,
            "required_distance_pct": 1.5,
            "passed": price_break
        },
        "overall_passed": tight_base and contraction_ok and vol_spike and price_break
    }

def print_complete_analysis(results: Dict):
    """Print complete July analysis"""
    print("\n" + "="*100)
    print("📊 PRTS JULY 2020 - COMPLETE BREAKOUT ANALYSIS")
    print("="*100)
    
    print(f"📈 Symbol: {results['symbol']}")
    print(f"📅 Month: {results['month']}")
    print(f"📊 Trading Days: {results['total_days']}")
    
    print(f"\n📋 DAILY BREAKOUT ANALYSIS:")
    print("="*100)
    
    for analysis in results['daily_analysis']:
        date = analysis['date']
        price = analysis['price']
        change = analysis['daily_change_pct']
        volume = analysis['volume']
        rsi = analysis['rsi']
        
        print(f"\n📅 {date} - ${price:.2f} ({change:+.1f}%) | Vol: {volume:,.0f} | RSI: {rsi:.0f}")
        print("-" * 80)
        
        # Flag breakout analysis
        flag = analysis['flag_breakout']
        print(f"🚩 FLAG BREAKOUT ANALYSIS:")
        print(f"  Prior Impulse: {'✅' if flag['prior_impulse']['passed'] else '❌'} "
              f"({flag['prior_impulse']['best_impulse_pct']:.1f}% vs required 30%)")
        print(f"  Higher Lows: {'✅' if flag['higher_lows']['passed'] else '❌'} "
              f"({flag['higher_lows']['count']}/{flag['higher_lows']['total_days']} = {flag['higher_lows']['percentage']:.1f}%)")
        print(f"  ATR Contraction: {'✅' if flag['atr_contraction']['passed'] else '❌'} "
              f"({flag['atr_contraction']['ratio']:.3f} vs required < 1.0)")
        print(f"  Breakout Above High: {'✅' if flag['breakout_above_high']['passed'] else '❌'} "
              f"(${flag['breakout_above_high']['current_price']:.2f} vs ${flag['breakout_above_high']['required_price']:.2f})")
        print(f"  OVERALL FLAG: {'✅ PASSED' if flag['overall_passed'] else '❌ FAILED'}")
        
        # Range breakout analysis
        range_break = analysis['range_breakout']
        print(f"\n📦 RANGE BREAKOUT ANALYSIS:")
        print(f"  Tight Base: {'✅' if range_break['tight_base']['passed'] else '❌'} "
              f"({range_break['tight_base']['range_pct']:.1f}% vs required ≤ 15%)")
        print(f"  ATR Contraction: {'✅' if range_break['atr_contraction']['passed'] else '❌'} "
              f"({range_break['atr_contraction']['ratio']:.3f} vs required ≤ 0.8)")
        print(f"  Volume Expansion: {'✅' if range_break['volume_expansion']['passed'] else '❌'} "
              f"({range_break['volume_expansion']['multiple']:.1f}x vs required ≥ 1.5x)")
        print(f"  Price Breakout: {'✅' if range_break['price_breakout']['passed'] else '❌'} "
              f"(${range_break['price_breakout']['current_price']:.2f} vs ${range_break['price_breakout']['min_break_price']:.2f})")
        print(f"  OVERALL RANGE: {'✅ PASSED' if range_break['overall_passed'] else '❌ FAILED'}")

def main():
    """Main complete July analysis"""
    print("🔍 PRTS July 2020 - Complete Breakout Analysis")
    
    # Define date range for July 2020
    start_date = datetime(2020, 7, 1)
    end_date = datetime(2020, 7, 31)
    
    try:
        # Fetch PRTS data
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        client = StockHistoricalDataClient(api_key, secret_key)
        
        # Get data for longer period to have enough history
        extended_start = datetime(2020, 5, 1)
        
        request = StockBarsRequest(
            symbol_or_symbols="PRTS",
            timeframe=TimeFrame.Day,
            start=extended_start,
            end=end_date
        )
        
        bars = client.get_stock_bars(request)
        
        if not bars or "PRTS" not in bars.data:
            print("❌ No PRTS data found")
            return
        
        prts_bars = bars.data["PRTS"]
        print(f"📊 Fetched {len(prts_bars)} PRTS bars")
        
        # Analyze complete July
        results = analyze_complete_july(prts_bars)
        
        # Print complete analysis
        print_complete_analysis(results)
        
        # Save results
        output_file = Path(__file__).parent / "prts_july_complete_analysis_2020.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Complete July analysis saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
