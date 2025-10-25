#!/usr/bin/env python3
"""
Enhanced Contraction Analysis - Full NASDAQ with all parameters
No alphabetical bias - random sampling from entire database
"""

import sys
import os
from pathlib import Path
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from dotenv import load_dotenv

# Add the alpaca module to path
sys.path.insert(0, str(Path(__file__).parent / "input" / "alpaca"))

from breakout.breakout_scanner import detect_contraction_setup, detect_flag_breakout_setup, detect_range_breakout_setup, format_breakout_signal
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from output.gmail.send_email import send_email

# Load API keys
load_dotenv('config/api_keys.env')

def main():
    """Enhanced Contraction Analysis with all parameters"""
    
    client = StockHistoricalDataClient(
        os.getenv('ALPACA_API_KEY'), 
        os.getenv('ALPACA_SECRET_KEY')
    )
    
    # Get filtered NASDAQ symbols with quality filters
    db_path = Path(__file__).parent / 'nasdaq_db' / 'nasdaq.db'
    
    with sqlite3.connect(db_path) as conn:
        # Use existing filter system from breakout_analysis.py
        query = '''
        SELECT DISTINCT symbol FROM nasdaq_prices 
        WHERE symbol NOT LIKE '%W' 
        AND symbol NOT LIKE '%R' 
        AND close >= 10.0
        AND close <= 500.0
        AND volume >= 100000
        ORDER BY symbol
        '''
        symbols_df = pd.read_sql_query(query, conn)
        all_symbols = symbols_df['symbol'].tolist()
    
    # Initialize signal lists for all 3 signal types
    flag_signals = []
    range_signals = []
    contraction_signals = []
    analyzed_count = 0
    
    for i, symbol in enumerate(all_symbols, 1):
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=90)
            request = StockBarsRequest(
                symbol_or_symbols=[symbol], 
                timeframe=TimeFrame.Day, 
                start=start_time, 
                end=end_time
            )
            bars = client.get_stock_bars(request)
            
            if bars and symbol in bars.data:
                symbol_bars = list(bars.data[symbol])
                if len(symbol_bars) >= 60:
                    analyzed_count += 1
                    
                    # Get actual price data
                    closes = np.array([float(b.close) for b in symbol_bars])
                    current_price = closes[-1]
                    prev_price = closes[-2]
                    price_change = ((current_price - prev_price) / prev_price) * 100
                    
                    # Check for all 3 signal types
                    flag_setup = detect_flag_breakout_setup(symbol_bars, symbol)
                    range_setup = detect_range_breakout_setup(symbol_bars, symbol)
                    contraction_setup = detect_contraction_setup(symbol_bars, symbol)
                    
                    # Calculate RSI manually
                    def calculate_rsi(prices, period=14):
                        deltas = np.diff(prices)
                        gains = np.where(deltas > 0, deltas, 0)
                        losses = np.where(deltas < 0, -deltas, 0)
                        avg_gain = np.mean(gains[-period:])
                        avg_loss = np.mean(losses[-period:])
                        if avg_loss == 0:
                            return 100
                        rs = avg_gain / avg_loss
                        rsi = 100 - (100 / (1 + rs))
                        return rsi
                    
                    rsi_actual = calculate_rsi(closes)
                    
                    # Check Flag Breakout
                    if flag_setup:
                        signal = format_breakout_signal(
                            symbol=symbol,
                            price=current_price,
                            change_pct=price_change,
                            rsi=rsi_actual,
                            tr_atr=1.0,  # Flag breakout doesn't use ATR ratio
                            setup_type="Flag Breakout"
                        )
                        flag_signals.append(signal)
                    
                    # Check Range Breakout
                    if range_setup:
                        meta = range_setup.meta
                        atr_ratio = meta.get('atr_ratio', 1.0)
                        signal = format_breakout_signal(
                            symbol=symbol,
                            price=current_price,
                            change_pct=price_change,
                            rsi=rsi_actual,
                            tr_atr=atr_ratio,
                            setup_type="Range Breakout"
                        )
                        range_signals.append(signal)
                    
                    # Check Contraction
                    if contraction_setup:
                        meta = contraction_setup.meta
                        atr_ratio = meta.get('atr_ratio', 1.0)
                        signal = format_breakout_signal(
                            symbol=symbol,
                            price=current_price,
                            change_pct=price_change,
                            rsi=rsi_actual,
                            tr_atr=atr_ratio,
                            setup_type="Contraction"
                        )
                        contraction_signals.append(signal)
                else:
                    pass  # Skip insufficient data
            else:
                pass  # Skip no data
        except Exception as e:
            pass  # Skip errors
    
    # Combine all signals
    all_signals = flag_signals + range_signals + contraction_signals
    
    # Send email if signals found
    if all_signals:
        email_body = ""
        for i, signal in enumerate(all_signals, 1):
            email_body += f"{i}. {signal}\n"
        
        # Send email
        try:
            # Use the signal type as subject
            signal_type = all_signals[0].split(" | ")[-1]  # Get signal type from first signal
            send_email("deniz@bora.box", signal_type, email_body)
            print(f"✅ Email sent with {len(all_signals)} signals")
        except Exception as e:
            print(f"❌ Email failed: {e}")
    else:
        print("📊 No signals found")

if __name__ == "__main__":
    main()
