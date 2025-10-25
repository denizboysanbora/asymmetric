#!/usr/bin/env python3
"""
Find breakout signals from yesterday (October 24th, 2025)
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def find_breakout_signals():
    # Connect to database
    conn = sqlite3.connect('nasdaq_db/nasdaq.db')
    
    # Get data for yesterday and previous days for breakout analysis
    yesterday = '2025-10-24'
    query = '''
    SELECT symbol, date, close, high, low, volume, rsi, atr
    FROM nasdaq_prices 
    WHERE date >= '2025-10-20' AND date <= '2025-10-24'
      AND close > 5
      AND volume > 100000
    ORDER BY symbol, date
    '''
    
    df = pd.read_sql_query(query, conn)
    print(f'📊 Analyzing {len(df)} records for breakout signals...')
    
    # Group by symbol and analyze for breakouts
    breakout_signals = []
    
    for symbol in df['symbol'].unique():
        symbol_data = df[df['symbol'] == symbol].sort_values('date')
        
        if len(symbol_data) < 3:  # Need at least 3 days of data
            continue
        
        # Get latest data
        latest = symbol_data.iloc[-1]
        prev_close = symbol_data.iloc[-2]['close'] if len(symbol_data) > 1 else latest['close']
        
        # Calculate price change
        price_change = ((latest['close'] - prev_close) / prev_close) * 100
        
        # Look for breakout criteria
        if (latest['rsi'] > 60 and 
            latest['volume'] > symbol_data['volume'].mean() * 1.5 and  # Volume spike
            price_change > 2.0 and  # Price increase > 2%
            latest['close'] > latest['high'] * 0.98):  # Near high of day
            
            breakout_signals.append({
                'symbol': symbol,
                'price': latest['close'],
                'change_pct': price_change,
                'rsi': latest['rsi'],
                'volume': latest['volume'],
                'atr': latest['atr']
            })
    
    # Sort by RSI and volume
    breakout_signals.sort(key=lambda x: (x['rsi'], x['volume']), reverse=True)
    
    print(f'\n🎯 Breakout Signals from {yesterday}:')
    print('=' * 60)
    for signal in breakout_signals[:10]:  # Top 10 signals
        print(f'${signal["symbol"]} ${signal["price"]:.2f} +{signal["change_pct"]:.1f}% | {signal["rsi"]:.0f} RSI | {signal["volume"]:,} vol | {signal["atr"]:.2f}x ATR')
    
    if not breakout_signals:
        print('❌ No breakout signals found for yesterday')
    
    # Also show high RSI stocks with volume
    print(f'\n📈 High RSI Stocks from {yesterday}:')
    print('=' * 60)
    
    high_rsi_query = '''
    SELECT symbol, close, volume, rsi, atr
    FROM nasdaq_prices 
    WHERE date = ? 
      AND rsi > 70 
      AND volume > 500000
      AND close > 5
    ORDER BY rsi DESC, volume DESC
    LIMIT 15
    '''
    
    high_rsi_df = pd.read_sql_query(high_rsi_query, conn, params=[yesterday])
    for _, row in high_rsi_df.iterrows():
        print(f'${row["symbol"]} ${row["close"]:.2f} | {row["rsi"]:.0f} RSI | {row["volume"]:,} vol | {row["atr"]:.2f}x ATR')
    
    conn.close()

if __name__ == "__main__":
    find_breakout_signals()
