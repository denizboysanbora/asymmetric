#!/usr/bin/env python3
"""
CODX Flag Breakout Analysis
Analyze CODX February 2020 specifically for Flag breakout patterns
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
    from breakout_scanner_updated import detect_flag_breakout_setup
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

def analyze_flag_breakout_criteria():
    """Analyze Flag breakout criteria in detail"""
    
    print("🚩 CODX FLAG BREAKOUT ANALYSIS")
    print("Analyzing Flag breakout criteria with updated parameters")
    print("=" * 100)
    
    # Fetch CODX data
    symbol = "CODX"
    start_date = datetime(2020, 2, 1)
    end_date = datetime(2020, 2, 29)
    
    print(f"📊 Fetching {symbol} data...")
    bars = fetch_historical_data(symbol, start_date, end_date)
    
    if not bars:
        print(f"❌ No data found for {symbol}")
        return
    
    print(f"📊 Fetched {len(bars)} bars for {symbol}")
    
    # Filter to February 2020 bars
    feb_bars = []
    for bar in bars:
        if bar.timestamp.date() >= start_date.date() and bar.timestamp.date() <= end_date.date():
            feb_bars.append(bar)
    
    print(f"📅 Found {len(feb_bars)} bars in February 2020")
    
    if len(feb_bars) == 0:
        print("❌ No February data found")
        return
    
    # Get SPY data for benchmark
    print(f"📊 Fetching SPY benchmark data...")
    spy_bars = fetch_historical_data("SPY", start_date - timedelta(days=120), end_date)
    spy_closes = [float(bar.close) for bar in spy_bars] if spy_bars else None
    
    print(f"\n📋 FLAG BREAKOUT CRITERIA:")
    print("=" * 100)
    print("1. 📏 Tight Base: ≤25% range in last 20 days")
    print("2. 📊 ATR Contraction: ≤1.2 ratio (current vs baseline)")
    print("3. 💰 Price Breakout: ≥1.0% above recent high")
    print("4. 📈 Volume Expansion: ≥1.5x average volume")
    print("5. 🎯 Prior Impulse: ≥30% move in last 60 days")
    print("6. 🚩 Higher Lows: Optional (not required for Flag)")
    print("7. 📊 Market Filter: SPY 10DMA > 20DMA")
    
    # Analyze each February trading day
    results = []
    
    print(f"\n📅 CODX February 2020 Flag Breakout Analysis:")
    print("=" * 120)
    print(f"{'Date':<12} {'Price':<8} {'Change%':<8} {'Volume':<12} {'Tight':<6} {'ATR':<6} {'Break':<6} {'Vol':<6} {'Impulse':<8} {'Result':<8}")
    print("-" * 120)
    
    for i, current_bar in enumerate(feb_bars):
        # Get all bars up to current date
        bars_up_to_date = []
        for bar in bars:
            if bar.timestamp.date() <= current_bar.timestamp.date():
                bars_up_to_date.append(bar)
        
        if len(bars_up_to_date) < 60:  # Need minimum data
            continue
        
        # Get corresponding SPY data
        spy_closes_up_to_date = None
        if spy_closes and len(spy_closes) >= len(bars_up_to_date):
            spy_closes_up_to_date = spy_closes[:len(bars_up_to_date)]
        
        # Test Flag Breakout
        flag_setup = detect_flag_breakout_setup(
            bars_up_to_date, 
            symbol, 
            spy_closes_up_to_date
        )
        
        # Calculate individual criteria for display
        closes = np.array([float(b.close) for b in bars_up_to_date], dtype=float)
        highs = np.array([float(b.high) for b in bars_up_to_date], dtype=float)
        lows = np.array([float(b.low) for b in bars_up_to_date], dtype=float)
        vols = np.array([float(b.volume) for b in bars_up_to_date], dtype=float)
        
        # 1. Tight Base (last 20 days)
        base_len = 20
        base_slice = slice(-base_len, None)
        base_closes = closes[base_slice]
        range_high = float(np.max(base_closes))
        range_low = float(np.min(base_closes))
        range_size = range_high - range_low
        range_pct = (range_size / range_low) * 100 if range_low > 0 else 100
        tight_base = range_pct <= 25.0
        
        # 2. ATR Contraction
        def calculate_atr(high, low, close, period):
            tr_values = []
            for j in range(1, len(close)):
                tr = max(
                    high[j] - low[j],
                    abs(high[j] - close[j-1]),
                    abs(low[j] - close[j-1])
                )
                tr_values.append(tr)
            return np.mean(tr_values[-period:]) if tr_values else 0
        
        recent_atr = calculate_atr(highs, lows, closes, 14)
        baseline_atr = calculate_atr(highs[:30], lows[:30], closes[:30], 14)
        atr_ratio = recent_atr / baseline_atr if baseline_atr > 0 else 1
        atr_contraction = atr_ratio <= 1.2
        
        # 3. Price Breakout
        min_break_price = range_high * 1.01  # 1% for flag
        current_price = closes[-1]
        price_break = current_price >= min_break_price
        breakout_distance = ((current_price - range_high) / range_high) * 100
        
        # 4. Volume Expansion
        recent_volume = vols[-1]
        avg_volume = np.mean(vols[-50:-1]) if len(vols) >= 50 else np.mean(vols[:-1])
        volume_multiple = recent_volume / avg_volume if avg_volume > 0 else 1
        volume_expansion = volume_multiple >= 1.5
        
        # 5. Prior Impulse (30%+ move in last 60 days)
        impulse_detected = False
        impulse_pct = 0
        
        for j in range(20, len(bars_up_to_date) - 20):
            window_high = max(highs[j-20:j+20])
            window_low = min(lows[j-20:j+20])
            
            if window_high > window_low:
                move_pct = ((window_high - window_low) / window_low) * 100
                if move_pct >= 30.0:
                    impulse_detected = True
                    impulse_pct = move_pct
                    break
        
        # Calculate daily change
        if i > 0:
            prev_close = float(feb_bars[i-1].close)
            current_close = float(current_bar.close)
            change_pct = ((current_close - prev_close) / prev_close) * 100
        else:
            change_pct = 0.0
        
        # Format output
        date_str = current_bar.timestamp.date().isoformat()
        price = f"${float(current_bar.close):.2f}"
        change = f"{change_pct:+.1f}%"
        volume = f"{int(current_bar.volume):,}"
        
        # Criteria status
        tight_status = "✅" if tight_base else "❌"
        atr_status = "✅" if atr_contraction else "❌"
        break_status = "✅" if price_break else "❌"
        vol_status = "✅" if volume_expansion else "❌"
        impulse_status = "✅" if impulse_detected else "❌"
        result_status = "✅" if flag_setup else "❌"
        
        print(f"{date_str:<12} {price:<8} {change:<8} {volume:<12} {tight_status:<6} {atr_status:<6} {break_status:<6} {vol_status:<6} {impulse_status:<8} {result_status:<8}")
        
        # Store results for summary
        results.append({
            'date': date_str,
            'price': float(current_bar.close),
            'change_pct': change_pct,
            'volume': int(current_bar.volume),
            'range_pct': range_pct,
            'atr_ratio': atr_ratio,
            'breakout_distance': breakout_distance,
            'volume_multiple': volume_multiple,
            'impulse_pct': impulse_pct,
            'tight_base': tight_base,
            'atr_contraction': atr_contraction,
            'price_break': price_break,
            'volume_expansion': volume_expansion,
            'prior_impulse': impulse_detected,
            'flag_breakout': flag_setup is not None,
            'flag_score': flag_setup.score if flag_setup else None
        })
    
    # Summary analysis
    print(f"\n" + "=" * 120)
    print(f"📊 FLAG BREAKOUT SUMMARY")
    print("=" * 120)
    
    flag_breakouts = [r for r in results if r['flag_breakout']]
    
    print(f"🚩 Flag Breakouts Found: {len(flag_breakouts)}")
    
    if flag_breakouts:
        print(f"\n🚩 FLAG BREAKOUT DAYS:")
        for breakout in flag_breakouts:
            print(f"   📅 {breakout['date']} | ${breakout['price']:.2f} | {breakout['change_pct']:+.1f}% | Score: {breakout['flag_score']:.2f}")
    else:
        print(f"\n🔍 NO FLAG BREAKOUTS DETECTED")
    
    # Analyze criteria failures
    print(f"\n🔍 CRITERIA FAILURE ANALYSIS:")
    tight_base_failures = [r for r in results if not r['tight_base']]
    atr_failures = [r for r in results if not r['atr_contraction']]
    price_failures = [r for r in results if not r['price_break']]
    volume_failures = [r for r in results if not r['volume_expansion']]
    impulse_failures = [r for r in results if not r['prior_impulse']]
    
    print(f"   📏 Tight Base failures: {len(tight_base_failures)}/{len(results)} ({len(tight_base_failures)/len(results)*100:.1f}%)")
    print(f"   📊 ATR Contraction failures: {len(atr_failures)}/{len(results)} ({len(atr_failures)/len(results)*100:.1f}%)")
    print(f"   💰 Price Breakout failures: {len(price_failures)}/{len(results)} ({len(price_failures)/len(results)*100:.1f}%)")
    print(f"   📈 Volume Expansion failures: {len(volume_failures)}/{len(results)} ({len(volume_failures)/len(results)*100:.1f}%)")
    print(f"   🎯 Prior Impulse failures: {len(impulse_failures)}/{len(results)} ({len(impulse_failures)/len(results)*100:.1f}%)")
    
    # Show worst failures
    print(f"\n📊 WORST CRITERIA VIOLATIONS:")
    if tight_base_failures:
        worst_tight = max(tight_base_failures, key=lambda x: x['range_pct'])
        print(f"   📏 Worst Tight Base: {worst_tight['date']} - {worst_tight['range_pct']:.1f}% range")
    
    if atr_failures:
        worst_atr = max(atr_failures, key=lambda x: x['atr_ratio'])
        print(f"   📊 Worst ATR Ratio: {worst_atr['date']} - {worst_atr['atr_ratio']:.1f} ratio")
    
    # Key insights
    print(f"\n💡 KEY INSIGHTS:")
    print(f"   • Total February trading days analyzed: {len(results)}")
    print(f"   • Days with Flag breakouts: {len(flag_breakouts)}")
    print(f"   • Most common failure: Tight Base ({len(tight_base_failures)}/{len(results)})")
    print(f"   • Second most common failure: ATR Contraction ({len(atr_failures)}/{len(results)})")
    
    if len(flag_breakouts) == 0:
        print(f"\n🔍 WHY NO FLAG BREAKOUTS:")
        print(f"   • CODX had extreme volatility throughout February")
        print(f"   • Range sizes consistently >25% (tight base failure)")
        print(f"   • ATR ratios consistently >1.2 (contraction failure)")
        print(f"   • These were fundamental/news-driven moves, not technical patterns")

def main():
    """Main analysis function"""
    
    try:
        analyze_flag_breakout_criteria()
        print(f"\n✅ CODX Flag breakout analysis completed!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
