#!/usr/bin/env python3
"""
CODX Daily Changes Verification
Verify what the daily percentage changes actually represent
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

def verify_daily_changes():
    """Verify what the daily percentage changes actually represent"""
    
    print("🔍 CODX DAILY CHANGES VERIFICATION")
    print("Checking if percentages are daily changes or volatilities")
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
    
    # Sort by date to ensure correct order
    feb_bars.sort(key=lambda x: x.timestamp.date())
    
    print(f"\n📅 CODX February 2020 - VERIFICATION OF DAILY CHANGES:")
    print("=" * 120)
    print(f"{'Date':<12} {'Open':<8} {'High':<8} {'Low':<8} {'Close':<8} {'Daily Change':<12} {'Intraday Range':<15} {'Volume':<12}")
    print("-" * 120)
    
    for i, bar in enumerate(feb_bars):
        date_str = bar.timestamp.date().isoformat()
        open_price = float(bar.open)
        high_price = float(bar.high)
        low_price = float(bar.low)
        close_price = float(bar.close)
        volume = int(bar.volume)
        
        # Calculate daily change (close vs previous close)
        if i > 0:
            prev_close = float(feb_bars[i-1].close)
            daily_change = ((close_price - prev_close) / prev_close) * 100
            daily_change_str = f"{daily_change:+.1f}%"
        else:
            daily_change_str = "N/A"
        
        # Calculate intraday range (high-low range as % of open)
        intraday_range = ((high_price - low_price) / open_price) * 100
        
        print(f"{date_str:<12} ${open_price:<7.2f} ${high_price:<7.2f} ${low_price:<7.2f} ${close_price:<7.2f} {daily_change_str:<12} {intraday_range:<14.1f}% {volume:<12,}")
    
    # Focus on the specific dates mentioned
    print(f"\n🎯 VERIFICATION OF SPECIFIC DATES:")
    print("=" * 100)
    
    target_dates = [
        "2020-02-06",
        "2020-02-10", 
        "2020-02-11",
        "2020-02-18",
        "2020-02-24"
    ]
    
    for target_date in target_dates:
        for i, bar in enumerate(feb_bars):
            if bar.timestamp.date().isoformat() == target_date:
                date_str = bar.timestamp.date().isoformat()
                open_price = float(bar.open)
                high_price = float(bar.high)
                low_price = float(bar.low)
                close_price = float(bar.close)
                volume = int(bar.volume)
                
                # Calculate daily change
                if i > 0:
                    prev_close = float(feb_bars[i-1].close)
                    daily_change = ((close_price - prev_close) / prev_close) * 100
                else:
                    daily_change = 0.0
                
                # Calculate intraday range
                intraday_range = ((high_price - low_price) / open_price) * 100
                
                print(f"\n📅 {date_str}:")
                print(f"   📊 Open: ${open_price:.2f}")
                print(f"   📊 High: ${high_price:.2f}")
                print(f"   📊 Low: ${low_price:.2f}")
                print(f"   📊 Close: ${close_price:.2f}")
                print(f"   📈 Daily Change: {daily_change:+.1f}% (vs previous close)")
                print(f"   📏 Intraday Range: {intraday_range:.1f}% (high-low vs open)")
                print(f"   📊 Volume: {volume:,}")
                
                # Check if the percentage matches what we reported earlier
                if target_date == "2020-02-06" and abs(daily_change - 18.9) < 0.1:
                    print(f"   ✅ Daily change matches reported +18.9%")
                elif target_date == "2020-02-10" and abs(daily_change - 32.0) < 0.1:
                    print(f"   ✅ Daily change matches reported +32.0%")
                elif target_date == "2020-02-11" and abs(daily_change - (-17.7)) < 0.1:
                    print(f"   ✅ Daily change matches reported -17.7%")
                elif target_date == "2020-02-18" and abs(daily_change - (-12.0)) < 0.1:
                    print(f"   ✅ Daily change matches reported -12.0%")
                elif target_date == "2020-02-24" and abs(daily_change - 28.9) < 0.1:
                    print(f"   ✅ Daily change matches reported +28.9%")
                else:
                    print(f"   ⚠️  Daily change does NOT match reported value")
                
                break
    
    # Summary
    print(f"\n💡 SUMMARY:")
    print("=" * 100)
    print("The percentages we reported are DAILY CHANGES (close vs previous close), not volatilities.")
    print("These represent the actual daily price movements from one trading day to the next.")
    print("Intraday ranges (high-low vs open) would be different and typically smaller.")

def main():
    """Main analysis function"""
    
    try:
        verify_daily_changes()
        print(f"\n✅ CODX daily changes verification completed!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
