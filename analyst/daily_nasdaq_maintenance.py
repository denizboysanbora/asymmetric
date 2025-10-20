#!/usr/bin/env python3
"""
Daily NASDAQ Database Maintenance Script
Maintains rolling 90-day window by adding new day and removing oldest day
"""
import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
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
    print(f"Error importing Alpaca modules: {e}")
    sys.exit(1)

def get_all_nasdaq_symbols():
    """Get list of all NASDAQ symbols from the database"""
    
    db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq_90day.db"
    
    if not db_path.exists():
        print("❌ nasdaq_90day.db not found")
        return []
    
    conn = sqlite3.connect(db_path)
    symbols_df = pd.read_sql_query("SELECT DISTINCT symbol FROM nasdaq_prices ORDER BY symbol", conn)
    conn.close()
    
    return symbols_df['symbol'].tolist()

def get_database_date_range():
    """Get current date range in the database"""
    
    db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq_90day.db"
    
    if not db_path.exists():
        return None, None, 0
    
    conn = sqlite3.connect(db_path)
    result = conn.execute("SELECT MIN(date) as start_date, MAX(date) as end_date, COUNT(DISTINCT date) as trading_days FROM nasdaq_prices").fetchone()
    conn.close()
    
    return result[0], result[1], result[2] if result else None

def fetch_new_day_data(date: datetime, symbols: List[str]):
    """Fetch data for a specific date from Alpaca API"""
    
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    if not api_key or not secret_key:
        print("❌ No Alpaca API keys found")
        return None
    
    client = StockHistoricalDataClient(api_key, secret_key)
    
    print(f"📡 Fetching data for {date.strftime('%Y-%m-%d')}...")
    
    # Process symbols in batches to avoid API limits
    batch_size = 100
    all_data = []
    
    for i in range(0, len(symbols), batch_size):
        batch_symbols = symbols[i:i + batch_size]
        
        try:
            request = StockBarsRequest(
                symbol_or_symbols=batch_symbols,
                timeframe=TimeFrame.Day,
                start=date,
                end=date
            )
            
            bars = client.get_stock_bars(request)
            
            if bars and bars.data:
                for symbol, symbol_bars in bars.data.items():
                    if symbol_bars:  # Check if we have data for this symbol
                        bar = symbol_bars[0]  # Get the first (and only) bar for the date
                        all_data.append({
                            'symbol': symbol,
                            'date': date.strftime('%Y-%m-%d'),
                            'open': float(bar.open),
                            'high': float(bar.high),
                            'low': float(bar.low),
                            'close': float(bar.close),
                            'volume': float(bar.volume),
                            'adjusted_close': float(bar.close)  # Use close as adjusted_close for now
                        })
            
            print(f"   Batch {i//batch_size + 1}: Fetched data for {len([s for s in batch_symbols if s in [d['symbol'] for d in all_data]])} symbols")
            
        except Exception as e:
            print(f"⚠️  Error fetching batch {i//batch_size + 1}: {e}")
            continue
    
    print(f"✅ Fetched data for {len(all_data)} symbols")
    return all_data

def calculate_technical_indicators_for_date(df: pd.DataFrame, target_date: str):
    """Calculate technical indicators for a specific date"""
    
    # Sort by symbol and date
    df = df.sort_values(['symbol', 'date'])
    
    # Calculate technical indicators for each symbol
    def calc_indicators_for_symbol(group):
        closes = group['close'].values
        highs = group['high'].values
        lows = group['low'].values
        
        # Find the target date row
        target_idx = group[group['date'] == target_date].index
        if len(target_idx) == 0:
            return group
        
        target_idx = target_idx[0]
        group_idx = group.index.get_loc(target_idx)
        
        # RSI (14-period)
        if group_idx >= 14:
            recent_closes = closes[group_idx-14:group_idx+1]
            deltas = np.diff(recent_closes)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains)
            avg_loss = np.mean(losses)
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            group.loc[target_idx, 'rsi'] = rsi
        
        # ATR (14-period)
        if group_idx >= 14:
            atr_sum = 0
            for j in range(group_idx-13, group_idx+1):
                if j > 0:
                    tr = max(
                        highs[j] - lows[j],
                        abs(highs[j] - closes[j-1]),
                        abs(lows[j] - closes[j-1])
                    )
                    atr_sum += tr
            
            atr = atr_sum / 14
            group.loc[target_idx, 'atr'] = atr
        
        # SMA 20 and 50
        if group_idx >= 19:
            group.loc[target_idx, 'sma_20'] = np.mean(closes[group_idx-19:group_idx+1])
        
        if group_idx >= 49:
            group.loc[target_idx, 'sma_50'] = np.mean(closes[group_idx-49:group_idx+1])
        
        return group
    
    # Apply to each symbol
    result_df = df.groupby('symbol').apply(calc_indicators_for_symbol).reset_index(drop=True)
    return result_df

def add_new_day_to_database(new_data: List[Dict], target_date: str):
    """Add new day's data to the database"""
    
    db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq_90day.db"
    
    if not db_path.exists():
        print("❌ nasdaq_90day.db not found")
        return False
    
    conn = sqlite3.connect(db_path)
    
    # Get existing data to calculate technical indicators
    existing_df = pd.read_sql_query("SELECT * FROM nasdaq_prices ORDER BY symbol, date", conn)
    
    # Add new data
    new_df = pd.DataFrame(new_data)
    
    # Combine and calculate technical indicators
    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    combined_df = combined_df.sort_values(['symbol', 'date'])
    
    # Calculate technical indicators for the new date
    updated_df = calculate_technical_indicators_for_date(combined_df, target_date)
    
    # Insert new data
    new_records = updated_df[updated_df['date'] == target_date]
    
    if not new_records.empty:
        new_records.to_sql('nasdaq_prices', conn, if_exists='append', index=False)
        print(f"✅ Added {len(new_records)} records for {target_date}")
    
    conn.close()
    return True

def remove_oldest_day_from_database():
    """Remove the oldest day's data to maintain 90-day window"""
    
    db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq_90day.db"
    
    if not db_path.exists():
        print("❌ nasdaq_90day.db not found")
        return False
    
    conn = sqlite3.connect(db_path)
    
    # Get the oldest date
    oldest_date = conn.execute("SELECT MIN(date) FROM nasdaq_prices").fetchone()[0]
    
    # Count records to be deleted
    count_before = conn.execute("SELECT COUNT(*) FROM nasdaq_prices").fetchone()[0]
    
    # Delete oldest day's data
    conn.execute("DELETE FROM nasdaq_prices WHERE date = ?", (oldest_date,))
    
    # Count records after deletion
    count_after = conn.execute("SELECT COUNT(*) FROM nasdaq_prices").fetchone()[0]
    
    deleted_count = count_before - count_after
    
    conn.close()
    
    print(f"🗑️  Removed {deleted_count} records for {oldest_date}")
    return True

def main():
    """Main daily maintenance function"""
    
    print("🔧 Daily NASDAQ Database Maintenance")
    print("Adding new day and maintaining 90-day rolling window")
    print("=" * 60)
    
    try:
        # Check if database exists
        db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq_90day.db"
        if not db_path.exists():
            print("❌ nasdaq_90day.db not found. Please run consolidate_nasdaq_90day.py first.")
            return
        
        # Get current database status
        start_date, end_date, trading_days = get_database_date_range()
        print(f"📊 Current database: {start_date} to {end_date} ({trading_days} trading days)")
        
        # Determine target date (next trading day)
        if end_date:
            last_date = datetime.strptime(end_date, '%Y-%m-%d')
            target_date = last_date + timedelta(days=1)
            
            # Skip weekends (simple logic)
            while target_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
                target_date += timedelta(days=1)
        else:
            target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        print(f"📅 Target date: {target_date.strftime('%Y-%m-%d')}")
        
        # Check if target date is today or in the past
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if target_date > today:
            print("⚠️  Target date is in the future. No new data to fetch.")
            return
        
        # Get all symbols
        symbols = get_all_nasdaq_symbols()
        print(f"📊 Found {len(symbols)} symbols in database")
        
        # Fetch new day's data
        new_data = fetch_new_day_data(target_date, symbols)
        
        if new_data:
            # Add new day to database
            add_new_day_to_database(new_data, target_date.strftime('%Y-%m-%d'))
            
            # Remove oldest day to maintain 90-day window
            remove_oldest_day_from_database()
            
            # Verify final state
            start_date_new, end_date_new, trading_days_new = get_database_date_range()
            print(f"📊 Updated database: {start_date_new} to {end_date_new} ({trading_days_new} trading days)")
            
            print("\n✅ Daily maintenance completed successfully!")
        else:
            print("⚠️  No new data fetched. Maintenance skipped.")
    
    except Exception as e:
        print(f"❌ Error during daily maintenance: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
