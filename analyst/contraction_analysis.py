#!/usr/bin/env python3
"""
Contraction Analysis - Dynamic NASDAQ Scanner
Never hardcode stock lists - always use dynamic database queries
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

from breakout.breakout_scanner import detect_contraction_setup, format_breakout_signal
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# Load API keys
load_dotenv('config/api_keys.env')

class ContractionAnalyzer:
    """Dynamic NASDAQ Contraction Analysis - NO HARDCODED STOCKS"""
    
    def __init__(self):
        self.db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq_90day.db"
        self.client = StockHistoricalDataClient(
            os.getenv('ALPACA_API_KEY'), 
            os.getenv('ALPACA_SECRET_KEY')
        )
        
    def get_nasdaq_symbols(self, limit=None):
        """Get all NASDAQ symbols from database - NO HARDCODING"""
        if not self.db_path.exists():
            raise FileNotFoundError(f"NASDAQ database not found: {self.db_path}")
            
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT DISTINCT symbol FROM nasdaq_prices ORDER BY symbol"
            if limit:
                query += f" LIMIT {limit}"
            
            symbols_df = pd.read_sql_query(query, conn)
            return symbols_df['symbol'].tolist()
    
    def analyze_contraction_signals(self, max_stocks=None, top_n=10):
        """Analyze all NASDAQ stocks for Contraction signals"""
        print("🔍 Dynamic NASDAQ Contraction Analysis")
        print("=" * 50)
        print("📊 Contraction Criteria:")
        print("• Tight Range: ≤25% (20-day range)")
        print("• ATR Contraction: ≤0.80 (5-day vs 20-day ATR)")
        print("• Volume Drying: ≤50% of average volume")
        print("• Higher Lows: REMOVED (no longer required)")
        print()
        
        # Get all NASDAQ symbols dynamically
        try:
            symbols = self.get_nasdaq_symbols(limit=max_stocks)
            print(f"📈 Analyzing {len(symbols)} NASDAQ stocks dynamically...")
            print(f"🚫 NO HARDCODED STOCKS - Using database query")
            print()
        except Exception as e:
            print(f"❌ Error loading NASDAQ symbols: {e}")
            return []
        
        contraction_signals = []
        analyzed_count = 0
        error_count = 0
        
        for i, symbol in enumerate(symbols, 1):
            try:
                # Get recent data for analysis
                end_time = datetime.now()
                start_time = end_time - timedelta(days=90)
                
                request = StockBarsRequest(
                    symbol_or_symbols=[symbol], 
                    timeframe=TimeFrame.Day, 
                    start=start_time, 
                    end=end_time
                )
                bars = self.client.get_stock_bars(request)
                
                if bars and symbol in bars.data:
                    symbol_bars = list(bars.data[symbol])
                    if len(symbol_bars) >= 60:
                        analyzed_count += 1
                        contraction_setup = detect_contraction_setup(symbol_bars, symbol)
                        
                        if contraction_setup:
                            # Extract data from meta
                            meta = contraction_setup.meta
                            price = meta.get('price', 0)
                            change_pct = meta.get('pct_change', 0)
                            rsi = meta.get('rsi', 50)
                            atr_ratio = meta.get('atr_ratio', 1.0)
                            
                            # Format the signal
                            signal = format_breakout_signal(
                                symbol=symbol,
                                price=price,
                                change_pct=change_pct,
                                rsi=rsi,
                                tr_atr=atr_ratio,
                                setup_type=contraction_setup.setup
                            )
                            
                            print(f'✅ {symbol}: CONTRACTION SIGNAL')
                            print(f'   Signal: {signal}')
                            print(f'   Price: ${price:.2f}')
                            print(f'   Change: {change_pct:+.2f}%')
                            print(f'   RSI: {rsi:.0f}')
                            print(f'   ATR Ratio: {atr_ratio:.2f}')
                            print(f'   Range: {meta.get("range_pct", 0):.1f}%')
                            print(f'   Volume Mult: {meta.get("volume_mult", 1):.2f}x')
                            print()
                            
                            contraction_signals.append(signal)
                            
                            # Stop if we have enough signals
                            if len(contraction_signals) >= top_n:
                                break
                        else:
                            if i <= 10:  # Show first 10 failures for debugging
                                print(f'❌ {symbol}: No Contraction')
                    else:
                        if i <= 10:  # Show first 10 data issues
                            print(f'⚠️  {symbol}: Insufficient data ({len(symbol_bars)} bars)')
                else:
                    if i <= 10:  # Show first 10 data issues
                        print(f'❌ {symbol}: No data')
                        
            except Exception as e:
                error_count += 1
                if i <= 10:  # Show first 10 errors
                    print(f'❌ {symbol}: Error - {e}')
        
        # Summary
        print("=" * 80)
        print(f"📊 ANALYSIS SUMMARY:")
        print(f"   Total symbols in database: {len(symbols)}")
        print(f"   Successfully analyzed: {analyzed_count}")
        print(f"   Errors encountered: {error_count}")
        print(f"   Contraction signals found: {len(contraction_signals)}")
        print(f"   Success rate: {len(contraction_signals)/analyzed_count*100:.1f}%" if analyzed_count > 0 else "   Success rate: 0%")
        
        if contraction_signals:
            print(f"\n🎯 CONTRACTION SIGNALS FOUND: {len(contraction_signals)}")
            print("\n📝 SIGNAL FORMAT:")
            for i, signal in enumerate(contraction_signals, 1):
                print(f"{i}. {signal}")
        else:
            print("\n📊 No Contraction signals found")
            print("💡 Contraction signals are rare and indicate strong consolidation")
            print("💡 The criteria are very strict: tight range + ATR contraction + volume drying")
        
        return contraction_signals

def main():
    """Main function - uses dynamic NASDAQ database queries only"""
    
    print("✅ Using dynamic NASDAQ database queries only")
    print("🚫 NO HARDCODED STOCK LISTS - All symbols from database")
    print()
    
    # Run analysis
    analyzer = ContractionAnalyzer()
    
    try:
        signals = analyzer.analyze_contraction_signals(max_stocks=100, top_n=10)
        return signals
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return []

if __name__ == "__main__":
    main()
