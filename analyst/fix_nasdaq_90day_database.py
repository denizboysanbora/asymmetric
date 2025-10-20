#!/usr/bin/env python3
"""
Fix NASDAQ 90-Day Database
Re-creates the database with ALL symbols from the original monthly databases
"""
import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

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
        
        # Initialize arrays
        rsi_values = [np.nan] * len(closes)
        atr_values = [np.nan] * len(closes)
        sma20_values = [np.nan] * len(closes)
        sma50_values = [np.nan] * len(closes)
        
        # RSI (14-period)
        for i in range(14, len(closes)):
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
            
            rsi_values[i] = rsi
        
        # ATR (14-period)
        tr_values = []
        for i in range(len(closes)):
            if i == 0:
                tr_values.append(highs[i] - lows[i])
            else:
                tr = max(
                    highs[i] - lows[i],
                    abs(highs[i] - closes[i-1]),
                    abs(lows[i] - closes[i-1])
                )
                tr_values.append(tr)
        
        # Calculate ATR as 14-period SMA of TR
        for i in range(14, len(closes)):
            atr = np.mean(tr_values[i-13:i+1])
            atr_values[i] = atr
        
        # SMA 20 and 50
        for i in range(20, len(closes)):
            sma20_values[i] = np.mean(closes[i-19:i+1])
        
        for i in range(50, len(closes)):
            sma50_values[i] = np.mean(closes[i-49:i+1])
        
        group['rsi'] = rsi_values
        group['atr'] = atr_values
        group['sma_20'] = sma20_values
        group['sma_50'] = sma50_values
        
        return group
    
    # Apply to each symbol
    result_df = df.groupby('symbol').apply(calc_indicators_for_symbol, include_groups=False).reset_index(drop=True)
    
    print(f"✅ Technical indicators calculated")
    return result_df

def recreate_nasdaq_90day_database():
    """Re-create the nasdaq_90day.db with ALL symbols"""
    
    print("🔧 Re-creating NASDAQ 90-day database with ALL symbols...")
    
    # First, let's see what we have in the current database
    current_db = Path(__file__).parent / "nasdaq_db" / "nasdaq_90day.db"
    if current_db.exists():
        conn = sqlite3.connect(current_db)
        current_symbols = pd.read_sql_query("SELECT DISTINCT symbol FROM nasdaq_prices", conn)
        conn.close()
        print(f"📊 Current database has {len(current_symbols)} symbols")
    
    # Since we deleted the monthly databases, we need to recreate from scratch
    # Let's check if we have any backup or if we need to fetch from Alpaca API
    
    print("⚠️  Monthly databases were deleted. We need to recreate the database.")
    print("💡 Options:")
    print("   1. Fetch ALL symbols from Alpaca API (will take time)")
    print("   2. Use a smaller subset for testing")
    print("   3. Restore from backup if available")
    
    # For now, let's create a comprehensive database by fetching from Alpaca API
    # But let's do it in a more efficient way
    
    return False  # Indicate we need manual intervention

def main():
    """Main fix function"""
    
    print("🔧 Fix NASDAQ 90-Day Database")
    print("Re-creating database with ALL symbols")
    print("=" * 60)
    
    # Check current state
    db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq_90day.db"
    
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        
        # Get current stats
        stats = conn.execute("""
            SELECT 
                COUNT(DISTINCT symbol) as symbols,
                MIN(date) as start_date,
                MAX(date) as end_date,
                COUNT(*) as total_records
            FROM nasdaq_prices
        """).fetchone()
        
        conn.close()
        
        print(f"📊 Current database stats:")
        print(f"   Symbols: {stats[0]}")
        print(f"   Date range: {stats[1]} to {stats[2]}")
        print(f"   Total records: {stats[3]}")
        
        if stats[0] < 100:  # Less than 100 symbols indicates incomplete data
            print(f"⚠️  Database appears incomplete (only {stats[0]} symbols)")
            print("💡 Need to recreate with ALL symbols")
            
            # Ask for confirmation
            response = input("Do you want to recreate the database with ALL symbols? (y/N): ")
            if response.lower() == 'y':
                recreate_nasdaq_90day_database()
            else:
                print("❌ Database recreation cancelled")
        else:
            print("✅ Database appears to have sufficient symbols")
    else:
        print("❌ nasdaq_90day.db not found")
        recreate_nasdaq_90day_database()

if __name__ == "__main__":
    main()
