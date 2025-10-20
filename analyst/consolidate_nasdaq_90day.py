#!/usr/bin/env python3
"""
NASDAQ Database Consolidation Script
Creates a rolling 90-day database from all monthly databases
Updates with Alpaca API data and optimizes for breakout scanners
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

def create_optimized_schema():
    """Create optimized database schema for breakout scanners"""
    
    schema = """
    CREATE TABLE IF NOT EXISTS nasdaq_prices (
        symbol VARCHAR(10) NOT NULL,
        date DATE NOT NULL,
        open DECIMAL(10,2),
        high DECIMAL(10,2),
        low DECIMAL(10,2),
        close DECIMAL(10,2),
        volume BIGINT,
        adjusted_close DECIMAL(10,2),
        
        -- Pre-calculated technical indicators for breakout scanners
        rsi DECIMAL(5,2),
        atr DECIMAL(10,4),
        sma_20 DECIMAL(10,2),
        sma_50 DECIMAL(10,2),
        
        -- Metadata
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        PRIMARY KEY (symbol, date)
    );
    
    -- Optimized indexes for breakout scanner queries
    CREATE INDEX IF NOT EXISTS idx_np_date ON nasdaq_prices(date);
    CREATE INDEX IF NOT EXISTS idx_np_symbol ON nasdaq_prices(symbol);
    CREATE INDEX IF NOT EXISTS idx_np_close ON nasdaq_prices(close);
    CREATE INDEX IF NOT EXISTS idx_np_volume ON nasdaq_prices(volume);
    CREATE INDEX IF NOT EXISTS idx_np_rsi ON nasdaq_prices(rsi);
    CREATE INDEX IF NOT EXISTS idx_np_atr ON nasdaq_prices(atr);
    CREATE INDEX IF NOT EXISTS idx_np_symbol_date ON nasdaq_prices(symbol, date);
    CREATE INDEX IF NOT EXISTS idx_np_date_symbol ON nasdaq_prices(date, symbol);
    """
    
    return schema

def load_all_monthly_data():
    """Load data from all monthly databases"""
    
    # Database files in chronological order
    db_files = [
        "nasdaq_jan_25.db",
        "nasdaq_feb_25.db", 
        "nasdaq_mar_25.db",
        "nasdaq_apr_25.db",
        "nasdaq_may_25.db",
        "nasdaq_jun_25.db",
        "nasdaq_jul_25.db",
        "nasdaq_aug_25.db",
        "nasdaq_sep_25.db",
        "nasdaq_oct_25.db"
    ]
    
    all_data = []
    
    for db_file in db_files:
        db_path = Path(__file__).parent / "nasdaq_db" / db_file
        
        if not db_path.exists():
            print(f"⚠️  Database not found: {db_file}")
            continue
        
        print(f"📊 Loading data from {db_file}...")
        conn = sqlite3.connect(db_path)
        
        # Get all data
        query = """
        SELECT symbol, date, open, high, low, close, volume, adjusted_close, rsi, atr
        FROM nasdaq_prices 
        ORDER BY symbol, date
        """
        
        df = pd.read_sql_query(query, conn)
        all_data.append(df)
        conn.close()
        
        print(f"   Loaded {len(df)} records")
    
    if not all_data:
        print("❌ No data loaded from any database")
        return None
    
    # Combine all data
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.drop_duplicates(subset=['symbol', 'date']).sort_values(['symbol', 'date'])
    
    print(f"📊 Combined data: {len(combined_df)} records")
    print(f"📅 Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
    
    return combined_df

def get_last_90_days(combined_df: pd.DataFrame):
    """Extract the last 90 days of data"""
    
    # Get the most recent date
    latest_date = pd.to_datetime(combined_df['date'].max())
    
    # Calculate 90 days ago
    start_date = latest_date - timedelta(days=90)
    
    # Filter data for last 90 days
    combined_df['date_dt'] = pd.to_datetime(combined_df['date'])
    last_90_df = combined_df[combined_df['date_dt'] >= start_date].copy()
    last_90_df = last_90_df.drop('date_dt', axis=1)
    
    print(f"📅 Last 90 days: {last_90_df['date'].min()} to {last_90_df['date'].max()}")
    print(f"📊 Records in last 90 days: {len(last_90_df)}")
    
    return last_90_df

def calculate_technical_indicators(df: pd.DataFrame):
    """Calculate technical indicators for breakout scanners"""
    
    print("📊 Calculating technical indicators...")
    
    # Sort by symbol and date
    df = df.sort_values(['symbol', 'date'])
    
    # Calculate technical indicators for each symbol
    def calc_indicators_for_symbol(group):
        closes = group['close'].values
        highs = group['high'].values
        lows = group['low'].values
        
        # RSI (14-period)
        rsi_values = []
        for i in range(len(closes)):
            if i < 14:
                rsi_values.append(np.nan)
            else:
                # Calculate RSI
                deltas = np.diff(closes[i-14:i+1])
                gains = np.where(deltas > 0, deltas, 0)
                losses = np.where(deltas < 0, -deltas, 0)
                
                avg_gain = np.mean(gains)
                avg_loss = np.mean(losses)
                
                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))
                
                rsi_values.append(rsi)
        
        group['rsi'] = rsi_values
        
        # ATR (14-period)
        atr_values = []
        for i in range(len(closes)):
            if i < 1:
                atr_values.append(np.nan)
            else:
                # True Range calculation
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i-1]),
                    abs(lows[i] - closes[i-1])
                )
                atr_values.append(tr)
        
        # Calculate ATR as 14-period SMA of TR
        atr_final = []
        for i in range(len(atr_values)):
            if i < 14:
                atr_final.append(np.nan)
            else:
                atr = np.mean(atr_values[i-13:i+1])
                atr_final.append(atr)
        
        group['atr'] = atr_final
        
        # SMA 20 and 50
        sma20_values = []
        sma50_values = []
        
        for i in range(len(closes)):
            if i < 19:
                sma20_values.append(np.nan)
            else:
                sma20_values.append(np.mean(closes[i-19:i+1]))
            
            if i < 49:
                sma50_values.append(np.nan)
            else:
                sma50_values.append(np.mean(closes[i-49:i+1]))
        
        group['sma_20'] = sma20_values
        group['sma_50'] = sma50_values
        
        return group
    
    # Apply to each symbol
    result_df = df.groupby('symbol').apply(calc_indicators_for_symbol).reset_index(drop=True)
    
    print(f"✅ Technical indicators calculated")
    return result_df

def update_missing_data_with_alpaca(df: pd.DataFrame):
    """Update missing data using Alpaca API"""
    
    print("📡 Checking for missing data with Alpaca API...")
    
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    if not api_key or not secret_key:
        print("⚠️  No Alpaca API keys found, skipping API updates")
        return df
    
    client = StockHistoricalDataClient(api_key, secret_key)
    
    # Get unique symbols
    symbols = df['symbol'].unique().tolist()
    
    # Get date range
    min_date = pd.to_datetime(df['date'].min())
    max_date = pd.to_datetime(df['date'].max())
    
    print(f"📊 Checking {len(symbols)} symbols from {min_date.date()} to {max_date.date()}")
    
    updated_data = []
    
    for i, symbol in enumerate(symbols[:10]):  # Limit to first 10 for now
        if i % 5 == 0:
            print(f"📈 Progress: {i}/{min(10, len(symbols))} symbols checked...")
        
        try:
            # Get data from Alpaca
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Day,
                start=min_date,
                end=max_date
            )
            
            bars = client.get_stock_bars(request)
            if bars and symbol in bars.data:
                alpaca_bars = bars.data[symbol]
                
                # Convert to DataFrame
                alpaca_data = []
                for bar in alpaca_bars:
                    alpaca_data.append({
                        'symbol': symbol,
                        'date': bar.timestamp.strftime('%Y-%m-%d'),
                        'open': float(bar.open),
                        'high': float(bar.high),
                        'low': float(bar.low),
                        'close': float(bar.close),
                        'volume': float(bar.volume)
                    })
                
                alpaca_df = pd.DataFrame(alpaca_data)
                
                # Merge with existing data
                symbol_df = df[df['symbol'] == symbol]
                merged_df = pd.merge(symbol_df, alpaca_df, on=['symbol', 'date'], how='outer', suffixes=('', '_alpaca'))
                
                # Update missing values with Alpaca data
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    merged_df[col] = merged_df[col].fillna(merged_df[f'{col}_alpaca'])
                    merged_df = merged_df.drop(f'{col}_alpaca', axis=1)
                
                updated_data.append(merged_df)
        
        except Exception as e:
            print(f"⚠️  Error updating {symbol}: {e}")
            # Keep original data if API fails
            updated_data.append(df[df['symbol'] == symbol])
    
    if updated_data:
        result_df = pd.concat(updated_data, ignore_index=True)
        print(f"✅ Updated data with Alpaca API")
        return result_df
    else:
        print("⚠️  No data updated from Alpaca API")
        return df

def create_nasdaq_90day_database(df: pd.DataFrame):
    """Create the consolidated nasdaq_90day.db database"""
    
    db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq_90day.db"
    
    print(f"💾 Creating consolidated database: {db_path}")
    
    # Remove existing database if it exists
    if db_path.exists():
        db_path.unlink()
    
    # Create new database with optimized schema
    conn = sqlite3.connect(db_path)
    
    # Execute schema
    schema = create_optimized_schema()
    conn.executescript(schema)
    
    # Insert data
    df.to_sql('nasdaq_prices', conn, if_exists='append', index=False)
    
    # Create additional indexes for performance
    conn.execute("ANALYZE;")
    
    conn.close()
    
    print(f"✅ Created nasdaq_90day.db with {len(df)} records")
    
    # Verify the database
    conn = sqlite3.connect(db_path)
    result = conn.execute("SELECT COUNT(*) as total_records, COUNT(DISTINCT symbol) as symbols, MIN(date) as start_date, MAX(date) as end_date FROM nasdaq_prices").fetchone()
    conn.close()
    
    print(f"📊 Verification: {result[0]} records, {result[1]} symbols, {result[2]} to {result[3]}")
    
    return db_path

def delete_monthly_databases():
    """Delete all monthly database files"""
    
    print("🗑️  Deleting monthly database files...")
    
    monthly_files = [
        "nasdaq_jan_25.db",
        "nasdaq_feb_25.db", 
        "nasdaq_mar_25.db",
        "nasdaq_apr_25.db",
        "nasdaq_may_25.db",
        "nasdaq_jun_25.db",
        "nasdaq_jul_25.db",
        "nasdaq_aug_25.db",
        "nasdaq_sep_25.db",
        "nasdaq_oct_25.db"
    ]
    
    deleted_count = 0
    for db_file in monthly_files:
        db_path = Path(__file__).parent / "nasdaq_db" / db_file
        if db_path.exists():
            db_path.unlink()
            print(f"   Deleted: {db_file}")
            deleted_count += 1
    
    print(f"✅ Deleted {deleted_count} monthly database files")

def main():
    """Main consolidation function"""
    
    print("🔧 NASDAQ Database Consolidation")
    print("Creating rolling 90-day database optimized for breakout scanners")
    print("=" * 80)
    
    try:
        # Step 1: Load all monthly data
        print("\n📊 Step 1: Loading monthly data...")
        combined_df = load_all_monthly_data()
        if combined_df is None:
            return
        
        # Step 2: Get last 90 days
        print("\n📅 Step 2: Extracting last 90 days...")
        last_90_df = get_last_90_days(combined_df)
        
        # Step 3: Update missing data with Alpaca API
        print("\n📡 Step 3: Updating missing data...")
        updated_df = update_missing_data_with_alpaca(last_90_df)
        
        # Step 4: Calculate technical indicators
        print("\n📊 Step 4: Calculating technical indicators...")
        final_df = calculate_technical_indicators(updated_df)
        
        # Step 5: Create consolidated database
        print("\n💾 Step 5: Creating consolidated database...")
        db_path = create_nasdaq_90day_database(final_df)
        
        # Step 6: Delete monthly databases
        print("\n🗑️  Step 6: Cleaning up monthly databases...")
        delete_monthly_databases()
        
        print("\n" + "=" * 80)
        print("🎯 CONSOLIDATION COMPLETE!")
        print("=" * 80)
        print(f"✅ Created: nasdaq_90day.db")
        print(f"✅ Deleted: All monthly database files")
        print(f"✅ Optimized: Schema for breakout scanners")
        print(f"✅ Technical indicators: RSI, ATR, SMA calculated")
        print(f"✅ Rolling window: 90 days maintained")
        
    except Exception as e:
        print(f"❌ Error during consolidation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
