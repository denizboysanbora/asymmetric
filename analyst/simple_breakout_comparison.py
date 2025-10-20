#!/usr/bin/env python3
"""
Simple Breakout Comparison
Direct comparison of actual breakout days vs our parameters
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

def create_comparison_table():
    """Create a simple comparison table"""
    
    print("🔍 BREAKOUT PARAMETERS COMPARISON TABLE")
    print("Comparing actual breakout days to our technical parameters")
    print("=" * 120)
    
    # Define our current parameters
    print(f"\n📋 CURRENT PARAMETERS:")
    print(f"   🚩 Flag Breakout:  Tight Base ≤25%, ATR ≤1.2, Price Break ≥1.0%, Volume ≥1.5x, Prior Impulse ≥30%, Higher Lows Optional")
    print(f"   📦 Range Breakout: Tight Base ≤25%, ATR ≤1.2, Higher Lows Required, Price Break ≥1.5%, Volume ≥1.5x")
    
    # Define actual breakout days with known metrics
    breakout_days = [
        {
            'symbol': 'APPS',
            'date': '2020-07-31',
            'type': 'Strong Move',
            'price': 13.88,
            'range_pct': 18.7,  # From our analysis
            'atr_ratio': 1.15,  # Estimated from volatility
            'higher_lows_pct': 55.0,  # From our analysis
            'volume_multiple': 2.6,  # From our analysis
            'breakout_distance': 3.89,  # Daily change
            'prior_impulse': False,
            'impulse_pct': 0.0
        },
        {
            'symbol': 'CODX',
            'date': '2020-02-26',
            'type': 'Massive Breakout',
            'price': 8.90,
            'range_pct': 791.4,  # From our analysis
            'atr_ratio': 3.5,  # Estimated from extreme volatility
            'higher_lows_pct': 30.0,  # Estimated
            'volume_multiple': 5.0,  # From our analysis
            'breakout_distance': 106.3,  # Daily change
            'prior_impulse': True,
            'impulse_pct': 50.0
        },
        {
            'symbol': 'CODX',
            'date': '2020-02-27',
            'type': 'Continuation',
            'price': 15.96,
            'range_pct': 791.4,  # Same period
            'atr_ratio': 3.5,  # Same period
            'higher_lows_pct': 30.0,  # Estimated
            'volume_multiple': 3.6,  # From our analysis
            'breakout_distance': 79.3,  # Daily change
            'prior_impulse': True,
            'impulse_pct': 50.0
        },
        {
            'symbol': 'CODX',
            'date': '2020-02-10',
            'type': 'Early Breakout',
            'price': 3.96,
            'range_pct': 50.0,  # Estimated
            'atr_ratio': 1.8,  # Estimated
            'higher_lows_pct': 40.0,  # Estimated
            'volume_multiple': 1.7,  # From our analysis
            'breakout_distance': 32.0,  # Daily change
            'prior_impulse': False,
            'impulse_pct': 15.0
        },
        {
            'symbol': 'CODX',
            'date': '2020-02-24',
            'type': 'Mid Breakout',
            'price': 3.93,
            'range_pct': 60.0,  # Estimated
            'atr_ratio': 2.0,  # Estimated
            'higher_lows_pct': 35.0,  # Estimated
            'volume_multiple': 0.8,  # From our analysis
            'breakout_distance': 28.9,  # Daily change
            'prior_impulse': True,
            'impulse_pct': 25.0
        }
    ]
    
    # Create comparison table
    print(f"\n📊 BREAKOUT DAYS vs PARAMETERS:")
    print("=" * 120)
    
    # Header
    print(f"{'Symbol':<8} {'Date':<12} {'Type':<15} {'Price':<8} {'Range%':<8} {'ATR':<6} {'HL%':<6} {'VolX':<6} {'Break%':<8} {'Imp%':<6}")
    print("-" * 120)
    
    # Data rows
    for day in breakout_days:
        print(f"{day['symbol']:<8} {day['date']:<12} {day['type']:<15} ${day['price']:<7.2f} {day['range_pct']:<7.1f}% {day['atr_ratio']:<5.1f} {day['higher_lows_pct']:<5.1f}% {day['volume_multiple']:<5.1f}x {day['breakout_distance']:<7.1f}% {day['impulse_pct']:<5.1f}%")
    
    # Parameter thresholds
    print(f"\n📋 PARAMETER THRESHOLDS:")
    print(f"   📏 Tight Base: ≤25%")
    print(f"   📊 ATR Ratio: ≤1.2 (Both Flag and Range)")
    print(f"   🚩 Higher Lows: Optional (Flag), Required ≥50% (Range)")
    print(f"   💰 Price Break: ≥1.0% (Flag), ≥1.5% (Range)")
    print(f"   📈 Volume: ≥1.5x")
    print(f"   🎯 Prior Impulse: ≥30% (Flag only)")
    
    # Detailed analysis
    print(f"\n🎯 DETAILED ANALYSIS:")
    print("=" * 120)
    
    for day in breakout_days:
        print(f"\n📊 {day['symbol']} - {day['date']} ({day['type']}):")
        
        # Check flag breakout criteria (higher lows is OPTIONAL)
        flag_criteria = {
            'tight_base': day['range_pct'] <= 25.0,
            'atr_contraction': day['atr_ratio'] <= 1.2,  # UPDATED: Both use 1.2 threshold
            'price_breakout': day['breakout_distance'] >= 1.0,
            'volume_expansion': day['volume_multiple'] >= 1.5,
            'prior_impulse': day['prior_impulse']
        }
        
        # Check range breakout criteria (higher lows is REQUIRED)
        range_criteria = {
            'tight_base': day['range_pct'] <= 25.0,
            'atr_contraction': day['atr_ratio'] <= 1.2,  # UPDATED: Both use 1.2 threshold
            'higher_lows': day['higher_lows_pct'] >= 50.0,  # Required for Range
            'price_breakout': day['breakout_distance'] >= 1.5,
            'volume_expansion': day['volume_multiple'] >= 1.5
        }
        
        flag_score = sum(flag_criteria.values())
        range_score = sum(range_criteria.values())
        
        print(f"   💰 Price: ${day['price']:.2f} | Volume: {day['volume_multiple']:.1f}x | Breakout: {day['breakout_distance']:+.1f}%")
        print(f"   📏 Range: {day['range_pct']:.1f}% | ATR: {day['atr_ratio']:.1f} | Higher Lows: {day['higher_lows_pct']:.1f}%")
        print(f"   🎯 Prior Impulse: {day['impulse_pct']:.1f}% ({'✅' if day['prior_impulse'] else '❌'})")
        
        print(f"   🚩 Flag Breakout Criteria:")
        for criterion, passed in flag_criteria.items():
            status = "✅" if passed else "❌"
            print(f"      {criterion}: {status}")
        print(f"   📊 Flag Score: {flag_score}/5")
        
        print(f"   📦 Range Breakout Criteria:")
        for criterion, passed in range_criteria.items():
            status = "✅" if passed else "❌"
            print(f"      {criterion}: {status}")
        print(f"   📊 Range Score: {range_score}/5")
    
    # Summary
    print(f"\n💡 SUMMARY & INSIGHTS:")
    print("=" * 120)
    
    print(f"🔍 Why These Breakouts Didn't Trigger Our Parameters:")
    print(f"   1. 📏 Tight Base: Most had ranges >25% (volatile periods)")
    print(f"   2. 📊 ATR Contraction: Most had ATR ratios >0.8 (high volatility)")
    print(f"   3. 🚩 Higher Lows: Some lacked the required 50% pattern")
    print(f"   4. 💰 Price Breakout: Some didn't break above recent highs by enough")
    print(f"   5. 📈 Volume: Some had volume but not enough expansion")
    print(f"   6. 🎯 Prior Impulse: Some lacked the required 30% prior move")
    
    print(f"\n🎯 Key Insights:")
    print(f"   • Our parameters are designed for 'clean' technical breakouts")
    print(f"   • These were more 'momentum/fundamental-driven' moves")
    print(f"   • High volatility periods often don't meet tight base criteria")
    print(f"   • ATR contraction is hard to achieve during volatile breakouts")
    print(f"   • Our system prioritizes quality over quantity")
    
    print(f"\n🔧 Potential Parameter Adjustments:")
    print(f"   • Tight Base: Could relax to 40-50% for volatile periods")
    print(f"   • ATR Contraction: Could relax to 1.2-1.5 for volatile breakouts")
    print(f"   • Higher Lows: Could make optional for flag breakouts")
    print(f"   • Volume: Could reduce to 1.2x for some setups")
    print(f"   • Prior Impulse: Could reduce to 20% for flag breakouts")

def main():
    """Main analysis function"""
    
    try:
        create_comparison_table()
        print(f"\n✅ Breakout parameters comparison completed!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
