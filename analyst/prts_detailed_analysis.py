#!/usr/bin/env python3
"""
Detailed PRTS Analysis - May-July 2020
Look for significant price movements and patterns
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
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

def analyze_price_action(bars: List[Bar]) -> Dict:
    """Analyze PRTS price action for significant moves and patterns"""
    if len(bars) < 10:
        return {"error": "Insufficient data"}
    
    closes = [float(bar.close) for bar in bars]
    highs = [float(bar.high) for bar in bars]
    lows = [float(bar.low) for bar in bars]
    volumes = [float(bar.volume) for bar in bars]
    dates = [bar.timestamp.date() for bar in bars]
    
    # Calculate daily returns
    returns = []
    for i in range(1, len(closes)):
        daily_return = (closes[i] - closes[i-1]) / closes[i-1] * 100
        returns.append(daily_return)
    
    # Find significant moves (>5% daily moves)
    significant_moves = []
    for i, ret in enumerate(returns):
        if abs(ret) >= 5.0:  # 5% or more move
            significant_moves.append({
                "date": dates[i+1],
                "return_pct": ret,
                "price": closes[i+1],
                "volume": volumes[i+1]
            })
    
    # Calculate key statistics
    total_return = (closes[-1] - closes[0]) / closes[0] * 100
    max_price = max(closes)
    min_price = min(closes)
    max_drawdown = 0
    peak = closes[0]
    
    for price in closes:
        if price > peak:
            peak = price
        drawdown = (peak - price) / peak * 100
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    # Find highest volume days
    avg_volume = np.mean(volumes)
    high_volume_days = []
    for i, vol in enumerate(volumes):
        if vol > avg_volume * 2:  # 2x average volume
            high_volume_days.append({
                "date": dates[i],
                "volume": vol,
                "volume_multiple": vol / avg_volume,
                "price": closes[i],
                "return_pct": returns[i-1] if i > 0 else 0
            })
    
    # Look for consolidation periods (low volatility)
    volatility_periods = []
    window_size = 10
    
    for i in range(window_size, len(closes)):
        window_returns = returns[i-window_size:i]
        volatility = np.std(window_returns)
        
        if volatility < 2.0:  # Low volatility threshold
            volatility_periods.append({
                "start_date": dates[i-window_size],
                "end_date": dates[i],
                "volatility": volatility,
                "price_range": (max(closes[i-window_size:i]) - min(closes[i-window_size:i])) / min(closes[i-window_size:i]) * 100
            })
    
    return {
        "symbol": "PRTS",
        "period": f"{dates[0]} to {dates[-1]}",
        "total_days": len(bars),
        "price_stats": {
            "start_price": closes[0],
            "end_price": closes[-1],
            "total_return_pct": total_return,
            "max_price": max_price,
            "min_price": min_price,
            "max_drawdown_pct": max_drawdown
        },
        "significant_moves": significant_moves,
        "high_volume_days": sorted(high_volume_days, key=lambda x: x['volume'], reverse=True),
        "low_volatility_periods": volatility_periods,
        "daily_data": [
            {
                "date": dates[i],
                "price": closes[i],
                "return_pct": returns[i-1] if i > 0 else 0,
                "volume": volumes[i],
                "high": highs[i],
                "low": lows[i]
            }
            for i in range(len(dates))
        ]
    }

def print_detailed_analysis(results: Dict):
    """Print detailed analysis results"""
    print("\n" + "="*70)
    print("📊 DETAILED PRTS ANALYSIS - May-July 2020")
    print("="*70)
    
    print(f"📈 Symbol: {results['symbol']}")
    print(f"📅 Period: {results['period']}")
    print(f"📊 Trading Days: {results['total_days']}")
    
    stats = results['price_stats']
    print(f"\n💰 PRICE STATISTICS:")
    print(f"  • Start Price: ${stats['start_price']:.2f}")
    print(f"  • End Price: ${stats['end_price']:.2f}")
    print(f"  • Total Return: {stats['total_return_pct']:+.2f}%")
    print(f"  • Highest Price: ${stats['max_price']:.2f}")
    print(f"  • Lowest Price: ${stats['min_price']:.2f}")
    print(f"  • Maximum Drawdown: {stats['max_drawdown_pct']:.2f}%")
    
    print(f"\n🚀 SIGNIFICANT MOVES (≥5%): {len(results['significant_moves'])}")
    if results['significant_moves']:
        for move in results['significant_moves']:
            print(f"  • {move['date']}: {move['return_pct']:+.1f}% to ${move['price']:.2f} (Vol: {move['volume']:,.0f})")
    else:
        print("  No significant daily moves detected")
    
    print(f"\n📈 HIGH VOLUME DAYS (2x+ Average): {len(results['high_volume_days'])}")
    if results['high_volume_days']:
        for vol_day in results['high_volume_days'][:5]:  # Top 5
            print(f"  • {vol_day['date']}: {vol_day['volume_multiple']:.1f}x volume ({vol_day['volume']:,.0f}) - ${vol_day['price']:.2f} ({vol_day['return_pct']:+.1f}%)")
    else:
        print("  No high volume days detected")
    
    print(f"\n📉 LOW VOLATILITY PERIODS: {len(results['low_volatility_periods'])}")
    if results['low_volatility_periods']:
        for period in results['low_volatility_periods']:
            print(f"  • {period['start_date']} to {period['end_date']}: {period['volatility']:.2f}% volatility, {period['price_range']:.1f}% range")
    else:
        print("  No low volatility periods detected")
    
    # Show daily price action
    print(f"\n📅 DAILY PRICE ACTION:")
    print("-" * 70)
    print("Date       | Price   | Return% | Volume     | High   | Low")
    print("-" * 70)
    
    for day in results['daily_data']:
        print(f"{day['date']} | ${day['price']:6.2f} | {day['return_pct']:+6.1f}% | {day['volume']:9,.0f} | ${day['high']:6.2f} | ${day['low']:6.2f}")

def main():
    """Main detailed analysis"""
    print("🔍 Detailed PRTS Analysis - May-July 2020")
    
    # Define date range
    start_date = datetime(2020, 5, 1)
    end_date = datetime(2020, 7, 31)
    
    try:
        # Fetch PRTS data
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        client = StockHistoricalDataClient(api_key, secret_key)
        
        request = StockBarsRequest(
            symbol_or_symbols="PRTS",
            timeframe=TimeFrame.Day,
            start=start_date,
            end=end_date
        )
        
        bars = client.get_stock_bars(request)
        
        if not bars or "PRTS" not in bars.data:
            print("❌ No PRTS data found")
            return
        
        prts_bars = bars.data["PRTS"]
        print(f"📊 Fetched {len(prts_bars)} PRTS bars")
        
        # Analyze price action
        results = analyze_price_action(prts_bars)
        
        # Print analysis
        print_detailed_analysis(results)
        
        # Save results
        output_file = Path(__file__).parent / "prts_detailed_analysis_2020.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed analysis saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
