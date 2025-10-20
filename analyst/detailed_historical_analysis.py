#!/usr/bin/env python3
"""
Detailed Historical Breakout Analysis
More comprehensive analysis of APPS July 2020 and CODX February 2020
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
    from breakout_scanner_updated import detect_flag_breakout_setup, detect_range_breakout_setup
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
        extended_start = start_date - timedelta(days=120)  # Get more historical data
        
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=extended_start,
            end=end_date
        )
        
        bars = client.get_stock_bars(request)
        
        if bars and symbol in bars.data and bars.data[symbol]:
            print(f"📊 Fetched {len(bars.data[symbol])} bars for {symbol}")
            return bars.data[symbol]
        else:
            print(f"❌ No data found for {symbol}")
            return None
            
    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {e}")
        return None

def analyze_price_action(bars: List[Bar], symbol: str, analysis_start: datetime, analysis_end: datetime):
    """Analyze price action and technical patterns"""
    
    if not bars or len(bars) < 30:
        return None
    
    # Convert to lists for analysis
    dates = [bar.timestamp.date() for bar in bars]
    opens = [float(bar.open) for bar in bars]
    highs = [float(bar.high) for bar in bars]
    lows = [float(bar.low) for bar in bars]
    closes = [float(bar.close) for bar in bars]
    volumes = [int(bar.volume) for bar in bars]
    
    # Find analysis period data
    analysis_bars = []
    for i, date in enumerate(dates):
        if analysis_start.date() <= date <= analysis_end.date():
            analysis_bars.append({
                'date': date,
                'open': opens[i],
                'high': highs[i],
                'low': lows[i],
                'close': closes[i],
                'volume': volumes[i]
            })
    
    if len(analysis_bars) < 5:
        print(f"❌ Insufficient data in analysis period for {symbol}")
        return None
    
    # Calculate key metrics
    analysis_closes = [bar['close'] for bar in analysis_bars]
    analysis_volumes = [bar['volume'] for bar in analysis_bars]
    
    start_price = analysis_closes[0]
    end_price = analysis_closes[-1]
    total_return = ((end_price - start_price) / start_price) * 100
    
    high_price = max([bar['high'] for bar in analysis_bars])
    low_price = min([bar['low'] for bar in analysis_bars])
    range_pct = ((high_price - low_price) / low_price) * 100
    
    avg_volume = np.mean(analysis_volumes)
    max_volume = max(analysis_volumes)
    volume_spike = max_volume / avg_volume if avg_volume > 0 else 1
    
    return {
        'symbol': symbol,
        'period': f"{analysis_start.date()} to {analysis_end.date()}",
        'days_analyzed': len(analysis_bars),
        'start_price': start_price,
        'end_price': end_price,
        'total_return_pct': total_return,
        'high_price': high_price,
        'low_price': low_price,
        'range_pct': range_pct,
        'avg_volume': avg_volume,
        'max_volume': max_volume,
        'volume_spike': volume_spike,
        'daily_data': analysis_bars
    }

def check_breakout_criteria(bars: List[Bar], symbol: str, analysis_start: datetime, analysis_end: datetime):
    """Check breakout criteria for the analysis period"""
    
    if not bars or len(bars) < 60:
        return None
    
    print(f"\n🔍 Checking breakout criteria for {symbol}...")
    
    # Get bars up to the end of analysis period
    analysis_bars = []
    for bar in bars:
        if bar.timestamp.date() <= analysis_end.date():
            analysis_bars.append(bar)
    
    if len(analysis_bars) < 60:
        print(f"❌ Insufficient data for breakout analysis: {len(analysis_bars)} bars")
        return None
    
    criteria_analysis = {
        'symbol': symbol,
        'total_bars': len(analysis_bars),
        'flag_breakout': None,
        'range_breakout': None,
        'criteria_details': {}
    }
    
    # Check flag breakout
    try:
        flag_setup = detect_flag_breakout_setup(
            bars=analysis_bars,
            symbol=symbol,
            benchmark_closes=None,
            base_len=20,
            max_range_width_pct=25.0,
            atr_len=14,
            atr_ma=50,
            atr_ratio_thresh=0.8,
            require_higher_lows=False,
            min_break_above_pct=1.0,
            vol_ma=50,
            vol_mult=1.5,
            use_market_filter=False
        )
        
        if flag_setup:
            criteria_analysis['flag_breakout'] = {
                'triggered': flag_setup.triggered,
                'score': flag_setup.score,
                'meta': flag_setup.meta
            }
            print(f"✅ Flag breakout detected! Score: {flag_setup.score:.3f}")
        else:
            print(f"❌ No flag breakout detected")
            
    except Exception as e:
        print(f"⚠️  Error checking flag breakout: {e}")
    
    # Check range breakout
    try:
        range_setup = detect_range_breakout_setup(
            bars=analysis_bars,
            symbol=symbol,
            benchmark_closes=None,
            base_len=20,
            max_range_width_pct=25.0,
            atr_len=14,
            atr_ma=50,
            atr_ratio_thresh=0.8,
            require_higher_lows=True,
            min_break_above_pct=1.5,
            vol_ma=50,
            vol_mult=1.5,
            use_market_filter=False
        )
        
        if range_setup:
            criteria_analysis['range_breakout'] = {
                'triggered': range_setup.triggered,
                'score': range_setup.score,
                'meta': range_setup.meta
            }
            print(f"✅ Range breakout detected! Score: {range_setup.score:.3f}")
        else:
            print(f"❌ No range breakout detected")
            
    except Exception as e:
        print(f"⚠️  Error checking range breakout: {e}")
    
    return criteria_analysis

def display_detailed_results(price_analysis: Dict, breakout_analysis: Dict):
    """Display detailed analysis results"""
    
    if not price_analysis:
        return
    
    symbol = price_analysis['symbol']
    period = price_analysis['period']
    
    print(f"\n" + "=" * 80)
    print(f"🎯 {symbol} DETAILED ANALYSIS RESULTS")
    print(f"📅 Period: {period}")
    print("=" * 80)
    
    # Price action summary
    print(f"📊 PRICE ACTION SUMMARY:")
    print(f"   📈 Start Price: ${price_analysis['start_price']:.2f}")
    print(f"   📈 End Price: ${price_analysis['end_price']:.2f}")
    print(f"   📊 Total Return: {price_analysis['total_return_pct']:+.2f}%")
    print(f"   📏 Price Range: ${price_analysis['low_price']:.2f} - ${price_analysis['high_price']:.2f}")
    print(f"   📏 Range Size: {price_analysis['range_pct']:.1f}%")
    print(f"   📊 Average Volume: {price_analysis['avg_volume']:,.0f}")
    print(f"   📊 Max Volume: {price_analysis['max_volume']:,.0f}")
    print(f"   📊 Volume Spike: {price_analysis['volume_spike']:.1f}x")
    
    # Breakout analysis
    if breakout_analysis:
        print(f"\n🎯 BREAKOUT ANALYSIS:")
        
        if breakout_analysis['flag_breakout']:
            flag = breakout_analysis['flag_breakout']
            print(f"   🚩 Flag Breakout: ✅ DETECTED (Score: {flag['score']:.3f})")
            if 'meta' in flag:
                meta = flag['meta']
                print(f"      📊 Prior Impulse: {meta.get('impulse_pct', 'N/A'):.1f}%")
                print(f"      📏 ATR Contraction: {meta.get('atr_contraction', 'N/A'):.3f}")
                print(f"      🚩 Higher Lows: {meta.get('higher_lows_count', 'N/A')}")
        else:
            print(f"   🚩 Flag Breakout: ❌ Not detected")
        
        if breakout_analysis['range_breakout']:
            range_brk = breakout_analysis['range_breakout']
            print(f"   📦 Range Breakout: ✅ DETECTED (Score: {range_brk['score']:.3f})")
            if 'meta' in range_brk:
                meta = range_brk['meta']
                print(f"      📏 Tight Base: {meta.get('tight_base', 'N/A')}")
                print(f"      📊 Range Pct: {meta.get('range_pct', 'N/A'):.1f}%")
                print(f"      📈 Volume Multiple: {meta.get('volume_mult', 'N/A'):.1f}x")
        else:
            print(f"   📦 Range Breakout: ❌ Not detected")
    
    # Daily breakdown for the analysis period
    print(f"\n📅 DAILY BREAKDOWN:")
    print("-" * 80)
    print(f"{'Date':<12} {'Open':<8} {'High':<8} {'Low':<8} {'Close':<8} {'Volume':<12} {'Change':<8}")
    print("-" * 80)
    
    for day in price_analysis['daily_data']:
        if len(price_analysis['daily_data']) > 1:
            prev_close = price_analysis['daily_data'][0]['close'] if day == price_analysis['daily_data'][0] else price_analysis['daily_data'][price_analysis['daily_data'].index(day)-1]['close']
            change = ((day['close'] - prev_close) / prev_close) * 100
        else:
            change = 0.0
        
        print(f"{day['date']:<12} ${day['open']:<7.2f} ${day['high']:<7.2f} ${day['low']:<7.2f} ${day['close']:<7.2f} {day['volume']:<12,} {change:+.2f}%")

def main():
    """Main analysis function"""
    
    print("🔍 Detailed Historical Breakout Analysis")
    print("Comprehensive analysis of APPS July 2020 and CODX February 2020")
    print("=" * 80)
    
    # Define analysis targets
    analyses = [
        {
            'symbol': 'APPS',
            'start_date': datetime(2020, 7, 1),
            'end_date': datetime(2020, 7, 31),
            'description': 'APPS in July 2020'
        },
        {
            'symbol': 'CODX',
            'start_date': datetime(2020, 2, 1),
            'end_date': datetime(2020, 2, 29),
            'description': 'CODX in February 2020'
        }
    ]
    
    all_results = []
    
    for analysis in analyses:
        symbol = analysis['symbol']
        start_date = analysis['start_date']
        end_date = analysis['end_date']
        description = analysis['description']
        
        print(f"\n📊 Fetching data for {description}...")
        
        # Fetch historical data
        bars = fetch_historical_data(symbol, start_date, end_date)
        
        if not bars:
            print(f"❌ Failed to fetch data for {symbol}")
            continue
        
        # Analyze price action
        price_analysis = analyze_price_action(bars, symbol, start_date, end_date)
        
        if not price_analysis:
            print(f"❌ Failed to analyze price action for {symbol}")
            continue
        
        # Check breakout criteria
        breakout_analysis = check_breakout_criteria(bars, symbol, start_date, end_date)
        
        # Display results
        display_detailed_results(price_analysis, breakout_analysis)
        
        # Save results
        results = {
            'price_analysis': price_analysis,
            'breakout_analysis': breakout_analysis
        }
        all_results.append(results)
        
        results_file = Path(__file__).parent / f"{symbol.lower()}_{start_date.year}_{start_date.month:02d}_detailed_results.json"
        import json
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {results_file}")
    
    # Save combined results
    if all_results:
        combined_file = Path(__file__).parent / "detailed_historical_analysis_results.json"
        import json
        with open(combined_file, 'w') as f:
            json.dump(all_results, f, indent=2, default=str)
        print(f"\n💾 Combined results saved to: {combined_file}")
    
    print(f"\n✅ Detailed historical analysis completed!")

if __name__ == "__main__":
    main()
