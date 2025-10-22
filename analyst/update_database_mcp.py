#!/usr/bin/env python3
"""
Update NASDAQ Database using Alpaca API with MCP-style approach
This script bypasses the MCP server and uses Alpaca API directly with better error handling
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

def fetch_data_with_retry(date: datetime, symbols: List[str], max_retries: int = 3):
    """Fetch data with retry logic and better error handling"""
    
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    if not api_key or not secret_key:
        print("❌ No Alpaca API keys found")
        return None
    
    try:
        client = StockHistoricalDataClient(api_key, secret_key)
    except Exception as e:
        print(f"❌ Failed to create Alpaca client: {e}")
        return None
    
    print(f"📡 Fetching data for {date.strftime('%Y-%m-%d')}...")
    
    # Process symbols in smaller batches to avoid API limits
    batch_size = 50
    all_data = []
    
    for attempt in range(max_retries):
        print(f"   Attempt {attempt + 1}/{max_retries}")
        
        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i:i + batch_size]
            
            try:
                # Try different date ranges to get data
                date_ranges = [
                    (date, date),  # Exact date
                    (date - timedelta(days=1), date + timedelta(days=1)),  # Range around date
                    (date - timedelta(days=2), date + timedelta(days=2)),  # Wider range
                ]
                
                batch_data = []
                for start_date, end_date in date_ranges:
                    try:
                        request = StockBarsRequest(
                            symbol_or_symbols=batch_symbols,
                            timeframe=TimeFrame.Day,
                            start=start_date,
                            end=end_date
                        )
                        
                        bars = client.get_stock_bars(request)
                        
                        if bars and bars.data:
                            print(f"   Batch {i//batch_size + 1}: Found data for {len(bars.data)} symbols")
                            
                            for symbol, symbol_bars in bars.data.items():
                                if symbol_bars:
                                    # Find the bar closest to our target date
                                    target_date = date.date()
                                    closest_bar = None
                                    min_diff = float('inf')
                                    
                                    for bar in symbol_bars:
                                        bar_date = bar.timestamp.date()
                                        diff = abs((bar_date - target_date).days)
                                        if diff < min_diff:
                                            min_diff = diff
                                            closest_bar = bar
                                    
                                    if closest_bar and min_diff <= 1:  # Within 1 day
                                        batch_data.append({
                                            'symbol': symbol,
                                            'date': target_date.strftime('%Y-%m-%d'),
                                            'open': float(closest_bar.open),
                                            'high': float(closest_bar.high),
                                            'low': float(closest_bar.low),
                                            'close': float(closest_bar.close),
                                            'volume': float(closest_bar.volume),
                                            'adjusted_close': float(closest_bar.close)
                                        })
                            
                            if batch_data:
                                break  # Found data, stop trying other date ranges
                    
                    except Exception as e:
                        print(f"   ⚠️  Error with date range {start_date} to {end_date}: {e}")
                        continue
                
                all_data.extend(batch_data)
                print(f"   Batch {i//batch_size + 1}: Processed {len(batch_data)} symbols")
                
            except Exception as e:
                print(f"   ⚠️  Error fetching batch {i//batch_size + 1}: {e}")
                continue
        
        if all_data:
            print(f"✅ Fetched data for {len(all_data)} symbols")
            return all_data
        else:
            print(f"   No data found in attempt {attempt + 1}")
            if attempt < max_retries - 1:
                print("   Retrying in 5 seconds...")
                import time
                time.sleep(5)
    
    print(f"❌ Failed to fetch data after {max_retries} attempts")
    return None

def calculate_technical_indicators_for_date(df: pd.DataFrame, target_date: str) -> pd.DataFrame:
    """Calculate technical indicators for a specific date"""
    
    # Ensure we have the data for the target date
    target_df = df[df['date'] == target_date].copy()
    
    if target_df.empty:
        return df
    
    # Calculate indicators for each symbol
    for symbol in target_df['symbol'].unique():
        symbol_data = df[df['symbol'] == symbol].sort_values('date')
        
        if len(symbol_data) < 20:  # Need at least 20 days for indicators
            continue
        
        # Get the row for the target date
        target_row = target_df[target_df['symbol'] == symbol]
        if target_row.empty:
            continue
        
        target_idx = target_row.index[0]
        
        # Calculate RSI (14-day)
        if len(symbol_data) >= 14:
            rsi = calculate_rsi(symbol_data['close'].values, 14)
            if len(rsi) > 0:
                df.loc[target_idx, 'rsi'] = rsi[-1]
        
        # Calculate ATR (14-day)
        if len(symbol_data) >= 14:
            atr = calculate_atr(symbol_data[['high', 'low', 'close']].values, 14)
            if len(atr) > 0:
                df.loc[target_idx, 'atr'] = atr[-1]
        
        # Calculate Z-Score (20-day)
        if len(symbol_data) >= 20:
            z_score = calculate_z_score(symbol_data['close'].values, 20)
            if len(z_score) > 0:
                df.loc[target_idx, 'z_score'] = z_score[-1]
        
        # Calculate ADR (20-day)
        if len(symbol_data) >= 20:
            adr = calculate_adr_pct(symbol_data[['high', 'low', 'close']].values, 20)
            if len(adr) > 0:
                df.loc[target_idx, 'adr_pct'] = adr[-1]
    
    return df

def calculate_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    """Calculate RSI indicator"""
    if len(prices) < period + 1:
        return np.array([])
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    rsi = np.zeros(len(prices) - period)
    
    for i in range(period, len(prices)):
        if avg_loss == 0:
            rsi[i - period] = 100
        else:
            rs = avg_gain / avg_loss
            rsi[i - period] = 100 - (100 / (1 + rs))
        
        if i < len(prices) - 1:
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    return rsi

def calculate_atr(hlc: np.ndarray, period: int = 14) -> np.ndarray:
    """Calculate ATR indicator"""
    if len(hlc) < period + 1:
        return np.array([])
    
    high, low, close = hlc[:, 0], hlc[:, 1], hlc[:, 2]
    
    tr = np.maximum(high[1:] - low[1:], 
                   np.maximum(np.abs(high[1:] - close[:-1]), 
                             np.abs(low[1:] - close[:-1])))
    
    atr = np.zeros(len(tr) - period + 1)
    atr[0] = np.mean(tr[:period])
    
    for i in range(1, len(atr)):
        atr[i] = (atr[i-1] * (period - 1) + tr[period + i - 1]) / period
    
    return atr

def calculate_z_score(prices: np.ndarray, period: int = 20) -> np.ndarray:
    """Calculate Z-Score indicator"""
    if len(prices) < period:
        return np.array([])
    
    z_scores = np.zeros(len(prices) - period + 1)
    
    for i in range(period - 1, len(prices)):
        window = prices[i - period + 1:i + 1]
        mean = np.mean(window)
        std = np.std(window)
        
        if std > 0:
            z_scores[i - period + 1] = (prices[i] - mean) / std
        else:
            z_scores[i - period + 1] = 0
    
    return z_scores

def calculate_adr_pct(hlc: np.ndarray, period: int = 20) -> np.ndarray:
    """Calculate ADR percentage indicator"""
    if len(hlc) < period:
        return np.array([])
    
    high, low, close = hlc[:, 0], hlc[:, 1], hlc[:, 2]
    
    adr_pct = np.zeros(len(hlc) - period + 1)
    
    for i in range(period - 1, len(hlc)):
        window_high = high[i - period + 1:i + 1]
        window_low = low[i - period + 1:i + 1]
        window_close = close[i - period + 1:i + 1]
        
        daily_ranges = (window_high - window_low) / window_close
        adr_pct[i - period + 1] = np.mean(daily_ranges) * 100
    
    return adr_pct

def update_database_with_new_data(new_data: List[Dict], target_date: str):
    """Update database with new data and calculate technical indicators"""
    
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
    
    if deleted_count > 0:
        print(f"🗑️  Removed {deleted_count} records from {oldest_date}")
    
    return True

def main():
    """Main function to update the database"""
    
    print("🔧 NASDAQ Database Update with MCP-style approach")
    print("=" * 50)
    
    # Get current database status
    start_date, end_date, trading_days = get_database_date_range()
    
    if not start_date:
        print("❌ Database not found")
        return
    
    print(f"📊 Current database: {start_date} to {end_date} ({trading_days} trading days)")
    
    # Determine target date (next trading day)
    from datetime import datetime, timedelta
    
    if end_date:
        last_date = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        last_date = datetime.now() - timedelta(days=30)
    
    # Find next trading day
    target_date = last_date + timedelta(days=1)
    while target_date.weekday() >= 5:  # Skip weekends
        target_date += timedelta(days=1)
    
    print(f"📅 Target date: {target_date.strftime('%Y-%m-%d')}")
    
    # Get symbols
    symbols = get_all_nasdaq_symbols()
    if not symbols:
        print("❌ No symbols found in database")
        return
    
    print(f"📊 Found {len(symbols)} symbols in database")
    
    # Fetch new data
    new_data = fetch_data_with_retry(target_date, symbols)
    
    if not new_data:
        print("⚠️  No new data fetched. Maintenance skipped.")
        return
    
    # Update database
    success = update_database_with_new_data(new_data, target_date.strftime('%Y-%m-%d'))
    
    if success:
        # Remove oldest day to maintain 90-day window
        remove_oldest_day_from_database()
        print("✅ Database update complete")
    else:
        print("❌ Database update failed")

if __name__ == "__main__":
    main()
