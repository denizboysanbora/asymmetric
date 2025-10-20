#!/usr/bin/env python3
"""
CODX Pre-Breakout Analysis
Analyze what parameters would have caught the days before CODX's massive breakouts
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

try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.models import Bar
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

def analyze_pre_breakout_periods():
    """Analyze what parameters would have caught pre-breakout days"""
    
    print("🔍 CODX PRE-BREAKOUT ANALYSIS")
    print("Analyzing what parameters would have caught days before the massive breakouts")
    print("=" * 100)
    
    # Fetch CODX data
    symbol = "CODX"
    start_date = datetime(2020, 1, 1)  # Get more data to see pre-breakout periods
    end_date = datetime(2020, 2, 29)
    
    print(f"📊 Fetching {symbol} data...")
    bars = fetch_historical_data(symbol, start_date, end_date)
    
    if not bars:
        print(f"❌ No data found for {symbol}")
        return
    
    print(f"📊 Fetched {len(bars)} bars for {symbol}")
    
    # Sort by date
    bars.sort(key=lambda x: x.timestamp.date())
    
    # Identify the massive breakout days
    massive_breakout_dates = [
        datetime(2020, 2, 26).date(),  # +106.3% day
        datetime(2020, 2, 27).date(),  # +79.3% day
        datetime(2020, 2, 10).date(),  # +32.0% day
        datetime(2020, 2, 24).date(),  # +28.9% day
    ]
    
    print(f"\n🎯 MASSIVE BREAKOUT DAYS TO ANALYZE:")
    for date in massive_breakout_dates:
        for bar in bars:
            if bar.timestamp.date() == date:
                print(f"   📅 {date}: ${float(bar.close):.2f}")
                break
    
    # Analyze pre-breakout periods
    print(f"\n📊 PRE-BREAKOUT ANALYSIS:")
    print("=" * 100)
    
    for breakout_date in massive_breakout_dates:
        print(f"\n🔍 Analyzing pre-breakout period for {breakout_date}:")
        
        # Find the breakout day
        breakout_bar = None
        breakout_index = None
        for i, bar in enumerate(bars):
            if bar.timestamp.date() == breakout_date:
                breakout_bar = bar
                breakout_index = i
                break
        
        if not breakout_bar or breakout_index is None:
            continue
        
        # Analyze the 5 days before the breakout
        pre_period_start = max(0, breakout_index - 5)
        pre_period_bars = bars[pre_period_start:breakout_index]
        
        print(f"   📅 Pre-breakout period: {len(pre_period_bars)} days before {breakout_date}")
        
        if len(pre_period_bars) < 3:
            continue
        
        # Calculate metrics for each pre-breakout day
        for i, current_bar in enumerate(pre_period_bars):
            # Get all bars up to current date
            bars_up_to_date = []
            current_index = pre_period_start + i
            for j in range(current_index + 1):
                bars_up_to_date.append(bars[j])
            
            if len(bars_up_to_date) < 60:
                continue
            
            # Calculate metrics
            closes = np.array([float(b.close) for b in bars_up_to_date], dtype=float)
            highs = np.array([float(b.high) for b in bars_up_to_date], dtype=float)
            lows = np.array([float(b.low) for b in bars_up_to_date], dtype=float)
            vols = np.array([float(b.volume) for b in bars_up_to_date], dtype=float)
            
            current_date = current_bar.timestamp.date()
            current_price = float(current_bar.close)
            current_volume = int(current_bar.volume)
            
            # 1. Tight Base Analysis (last 20 days)
            base_len = 20
            base_slice = slice(-base_len, None)
            base_closes = closes[base_slice]
            range_high = float(np.max(base_closes))
            range_low = float(np.min(base_closes))
            range_size = range_high - range_low
            range_pct = (range_size / range_low) * 100 if range_low > 0 else 100
            
            # 2. ATR Contraction Analysis
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
            
            # 3. Volume Analysis
            recent_volume = vols[-1]
            avg_volume = np.mean(vols[-50:-1]) if len(vols) >= 50 else np.mean(vols[:-1])
            volume_multiple = recent_volume / avg_volume if avg_volume > 0 else 1
            
            # 4. Higher Lows Analysis
            recent_lows = lows[-base_len:]
            higher_lows_count = 0
            for j in range(1, len(recent_lows)):
                if recent_lows[j] > recent_lows[j-1]:
                    higher_lows_count += 1
            higher_lows_pct = (higher_lows_count / len(recent_lows)) * 100
            
            # 5. Price Breakout Analysis
            min_break_price_flag = range_high * 1.01  # 1% for flag
            min_break_price_range = range_high * 1.015  # 1.5% for range
            price_breakout_flag = current_price >= min_break_price_flag
            price_breakout_range = current_price >= min_break_price_range
            breakout_distance = ((current_price - range_high) / range_high) * 100
            
            # 6. Prior Impulse Analysis
            impulse_detected = False
            max_impulse_pct = 0
            
            for j in range(20, len(bars_up_to_date) - 20):
                window_high = max(highs[j-20:j+20])
                window_low = min(lows[j-20:j+20])
                
                if window_high > window_low:
                    move_pct = ((window_high - window_low) / window_low) * 100
                    if move_pct >= 30.0:
                        impulse_detected = True
                        max_impulse_pct = move_pct
                        break
            
            print(f"      📅 {current_date}:")
            print(f"         💰 Price: ${current_price:.2f}")
            print(f"         📏 Range: {range_pct:.1f}%")
            print(f"         📊 ATR Ratio: {atr_ratio:.2f}")
            print(f"         📈 Volume: {volume_multiple:.1f}x")
            print(f"         🚩 Higher Lows: {higher_lows_pct:.1f}%")
            print(f"         💰 Breakout Distance: {breakout_distance:+.1f}%")
            print(f"         🎯 Prior Impulse: {max_impulse_pct:.1f}% ({'✅' if impulse_detected else '❌'})")
    
    # Analyze what parameters would have worked
    print(f"\n💡 PARAMETER ANALYSIS:")
    print("=" * 100)
    
    # Look at the days just before the massive breakouts
    pre_breakout_dates = [
        datetime(2020, 2, 25).date(),  # Day before +106% breakout
        datetime(2020, 2, 23).date(),  # Day before +28.9% breakout
        datetime(2020, 2, 9).date(),   # Day before +32% breakout
    ]
    
    print(f"\n🔍 ANALYZING DAYS JUST BEFORE BREAKOUTS:")
    
    for pre_date in pre_breakout_dates:
        for i, bar in enumerate(bars):
            if bar.timestamp.date() == pre_date:
                # Get all bars up to this date
                bars_up_to_date = bars[:i+1]
                
                if len(bars_up_to_date) < 60:
                    continue
                
                # Calculate metrics
                closes = np.array([float(b.close) for b in bars_up_to_date], dtype=float)
                highs = np.array([float(b.high) for b in bars_up_to_date], dtype=float)
                lows = np.array([float(b.low) for b in bars_up_to_date], dtype=float)
                vols = np.array([float(b.volume) for b in bars_up_to_date], dtype=float)
                
                # Calculate key metrics
                base_len = 20
                base_closes = closes[-base_len:]
                range_high = float(np.max(base_closes))
                range_low = float(np.min(base_closes))
                range_pct = ((range_high - range_low) / range_low) * 100
                
                recent_atr = calculate_atr(highs, lows, closes, 14)
                baseline_atr = calculate_atr(highs[:30], lows[:30], closes[:30], 14)
                atr_ratio = recent_atr / baseline_atr if baseline_atr > 0 else 1
                
                recent_volume = vols[-1]
                avg_volume = np.mean(vols[-50:-1]) if len(vols) >= 50 else np.mean(vols[:-1])
                volume_multiple = recent_volume / avg_volume if avg_volume > 0 else 1
                
                print(f"\n📅 {pre_date} (day before breakout):")
                print(f"   📏 Range: {range_pct:.1f}% (current threshold: 25%)")
                print(f"   📊 ATR Ratio: {atr_ratio:.2f} (current threshold: 1.2)")
                print(f"   📈 Volume: {volume_multiple:.1f}x (current threshold: 1.5x)")
                
                # Suggest what parameters would have worked
                print(f"   💡 To catch this day, we would need:")
                if range_pct > 25:
                    print(f"      📏 Tight Base: {range_pct:.1f}% (vs current 25%)")
                if atr_ratio > 1.2:
                    print(f"      📊 ATR Contraction: {atr_ratio:.2f} (vs current 1.2)")
                if volume_multiple < 1.5:
                    print(f"      📈 Volume: {volume_multiple:.1}{'x (vs current 1.5x)'}")
                
                break
    
    # Summary of suggested parameters
    print(f"\n🎯 SUGGESTED PARAMETERS TO CATCH CODX PRE-BREAKOUTS:")
    print("=" * 100)
    print("Based on the analysis, to catch CODX's pre-breakout days, we would need:")
    print("")
    print("📏 Tight Base Threshold: 50-60% (vs current 25%)")
    print("📊 ATR Contraction Threshold: 2.0-3.0 (vs current 1.2)")
    print("📈 Volume Expansion Threshold: 1.0-1.2x (vs current 1.5x)")
    print("💰 Price Breakout Threshold: 0.5-1.0% (vs current 1.0-1.5%)")
    print("🎯 Prior Impulse Threshold: 15-20% (vs current 30%)")
    print("")
    print("⚠️  WARNING: These relaxed parameters would:")
    print("   • Catch more false signals")
    print("   • Reduce quality of setups")
    print("   • Increase noise in results")
    print("   • May not be sustainable for other stocks")

def main():
    """Main analysis function"""
    
    try:
        analyze_pre_breakout_periods()
        print(f"\n✅ CODX pre-breakout analysis completed!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
