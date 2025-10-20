#!/usr/bin/env python3
"""
PRTS July 2020 Day-by-Day Breakout Analysis
Detailed analysis of why no breakouts were detected despite significant moves
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
    calculate_z_score,
    kristjan_checklist
)

def analyze_july_day_by_day(bars: List[Bar], spy_bars: List[Bar]) -> Dict:
    """Analyze PRTS July 2020 day by day with detailed breakout criteria"""
    
    # Filter for July 2020 bars
    july_bars = [bar for bar in bars if bar.timestamp.month == 7 and bar.timestamp.year == 2020]
    july_spy_bars = [bar for bar in spy_bars if bar.timestamp.month == 7 and bar.timestamp.year == 2020]
    
    if len(july_bars) < 5:
        return {"error": "Insufficient July data"}
    
    results = {
        "symbol": "PRTS",
        "month": "July 2020",
        "total_days": len(july_bars),
        "daily_analysis": []
    }
    
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
        
        # Detailed analysis of why breakouts weren't detected
        analysis = {
            "date": current_date,
            "price": closes[-1],
            "daily_change_pct": daily_change,
            "volume": volumes[-1],
            "rsi": rsi,
            "atr": atr,
            "z_score": z_score,
            "flag_breakout": flag_breakout is not None,
            "range_breakout": range_breakout is not None,
            "breakout_details": {}
        }
        
        # Analyze flag breakout criteria
        if flag_breakout:
            analysis["breakout_details"]["flag"] = {
                "score": flag_breakout.score,
                "triggered": flag_breakout.triggered,
                "meta": flag_breakout.meta
            }
        else:
            # Explain why no flag breakout
            flag_analysis = analyze_flag_criteria(historical_bars)
            analysis["breakout_details"]["flag"] = flag_analysis
        
        # Analyze range breakout criteria
        if range_breakout:
            analysis["breakout_details"]["range"] = {
                "score": range_breakout.score,
                "triggered": range_breakout.triggered,
                "meta": range_breakout.meta
            }
        else:
            # Explain why no range breakout
            range_analysis = analyze_range_criteria(historical_bars)
            analysis["breakout_details"]["range"] = range_analysis
        
        results["daily_analysis"].append(analysis)
    
    return results

def analyze_flag_criteria(bars: List[Bar]) -> Dict:
    """Analyze why flag breakout criteria weren't met"""
    if len(bars) < 60:
        return {"error": "Insufficient data"}
    
    closes = [float(bar.close) for bar in bars]
    highs = [float(bar.high) for bar in bars]
    lows = [float(bar.low) for bar in bars]
    
    # Check for prior impulse (30%+ move in last 60 days)
    impulse_detected = False
    impulse_pct = 0
    impulse_window = None
    
    for i in range(20, len(bars) - 20):
        window_high = max(highs[i-20:i+20])
        window_low = min(lows[i-20:i+20])
        
        if window_high > window_low:
            move_pct = (window_high - window_low) / window_low
            if move_pct >= 0.30:  # 30%+ move
                impulse_detected = True
                impulse_pct = move_pct * 100
                impulse_window = f"Days {i-20} to {i+20}"
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
    recent_high = max(recent_highs)
    current_price = recent_closes[-1]
    breakout_above_high = current_price > recent_high * 1.015  # 1.5% above recent high
    
    return {
        "impulse_detected": impulse_detected,
        "impulse_pct": impulse_pct,
        "impulse_window": impulse_window,
        "higher_lows_count": higher_lows,
        "higher_lows_pct": (higher_lows / len(recent_lows)) * 100 if len(recent_lows) > 0 else 0,
        "atr_contraction": atr_contraction,
        "atr_contraction_ok": atr_contraction < 1.0,
        "recent_high": recent_high,
        "current_price": current_price,
        "breakout_above_high": breakout_above_high,
        "breakout_distance_pct": ((current_price - recent_high) / recent_high * 100) if recent_high > 0 else 0
    }

def analyze_range_criteria(bars: List[Bar]) -> Dict:
    """Analyze why range breakout criteria weren't met"""
    if len(bars) < 60:
        return {"error": "Insufficient data"}
    
    closes = np.array([float(bar.close) for bar in bars])
    highs = np.array([float(bar.high) for bar in bars])
    lows = np.array([float(bar.low) for bar in bars])
    volumes = np.array([float(bar.volume) for bar in bars])
    
    # Range tightness (last 30 bars)
    base_len = 30
    base_slice = slice(-base_len, None)
    base_closes = closes[base_slice]
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
    price_break = closes[-1] >= min_break_price
    breakout_ok = price_break and vol_spike
    
    return {
        "range_high": range_high,
        "range_low": range_low,
        "range_size": range_size,
        "range_pct": range_pct,
        "tight_base": tight_base,
        "atr14": atr14,
        "atr50": atr50,
        "atr_ratio": atr_ratio,
        "contraction_ok": contraction_ok,
        "volume_current": volumes[-1],
        "volume_avg50": vol50,
        "volume_multiple": vol_mult,
        "vol_spike": vol_spike,
        "min_break_price": min_break_price,
        "current_price": closes[-1],
        "price_break": price_break,
        "breakout_ok": breakout_ok
    }

def print_july_analysis(results: Dict):
    """Print detailed July analysis"""
    print("\n" + "="*80)
    print("📊 PRTS JULY 2020 - DAY-BY-DAY BREAKOUT ANALYSIS")
    print("="*80)
    
    print(f"📈 Symbol: {results['symbol']}")
    print(f"📅 Month: {results['month']}")
    print(f"📊 Trading Days: {results['total_days']}")
    
    print(f"\n📋 DAILY BREAKOUT ANALYSIS:")
    print("-" * 80)
    
    for analysis in results['daily_analysis']:
        date = analysis['date']
        price = analysis['price']
        change = analysis['daily_change_pct']
        volume = analysis['volume']
        rsi = analysis['rsi']
        
        print(f"\n📅 {date} - ${price:.2f} ({change:+.1f}%) | Vol: {volume:,.0f} | RSI: {rsi:.0f}")
        
        # Flag breakout analysis
        flag_details = analysis['breakout_details']['flag']
        if 'error' not in flag_details:
            print(f"  🚩 FLAG BREAKOUT:")
            print(f"    • Prior Impulse: {'✅' if flag_details['impulse_detected'] else '❌'} "
                  f"({flag_details['impulse_pct']:.1f}%)")
            print(f"    • Higher Lows: {flag_details['higher_lows_count']}/20 "
                  f"({flag_details['higher_lows_pct']:.1f}%)")
            print(f"    • ATR Contraction: {'✅' if flag_details['atr_contraction_ok'] else '❌'} "
                  f"({flag_details['atr_contraction']:.3f})")
            print(f"    • Breakout Above High: {'✅' if flag_details['breakout_above_high'] else '❌'} "
                  f"(${flag_details['recent_high']:.2f} → ${flag_details['current_price']:.2f})")
        
        # Range breakout analysis
        range_details = analysis['breakout_details']['range']
        if 'error' not in range_details:
            print(f"  📦 RANGE BREAKOUT:")
            print(f"    • Tight Base: {'✅' if range_details['tight_base'] else '❌'} "
                  f"({range_details['range_pct']:.1f}% range)")
            print(f"    • ATR Contraction: {'✅' if range_details['contraction_ok'] else '❌'} "
                  f"({range_details['atr_ratio']:.3f})")
            print(f"    • Volume Spike: {'✅' if range_details['vol_spike'] else '❌'} "
                  f"({range_details['volume_multiple']:.1f}x)")
            print(f"    • Price Break: {'✅' if range_details['price_break'] else '❌'} "
                  f"(${range_details['min_break_price']:.2f})")

def main():
    """Main July analysis"""
    print("🔍 PRTS July 2020 - Detailed Breakout Analysis")
    
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
        
        # Get SPY data
        spy_request = StockBarsRequest(
            symbol_or_symbols="SPY",
            timeframe=TimeFrame.Day,
            start=extended_start,
            end=end_date
        )
        
        spy_data = client.get_stock_bars(spy_request)
        spy_bars = spy_data.data["SPY"] if "SPY" in spy_data.data else []
        
        print(f"📊 Fetched {len(prts_bars)} PRTS bars and {len(spy_bars)} SPY bars")
        
        # Analyze July day by day
        results = analyze_july_day_by_day(prts_bars, spy_bars)
        
        # Print analysis
        print_july_analysis(results)
        
        # Save results
        output_file = Path(__file__).parent / "prts_july_analysis_2020.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed July analysis saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
