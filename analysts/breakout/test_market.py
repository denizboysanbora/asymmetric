#!/usr/bin/env python3
"""
Quick market analysis test
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Set API keys
os.environ['ALPACA_API_KEY'] = 'PK5KN56VW1TVTL7X2GSJ'
os.environ['ALPACA_SECRET_KEY'] = 'Ojsiz7lO4SgTHRLLHz2nYxEoitOaKL1sOmGXAcz3'

# Add alpaca directory to path
ALPACA_DIR = Path(__file__).parent.parent / "input" / "alpaca"
sys.path.insert(0, str(ALPACA_DIR))

try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.models import Bar
except ImportError as e:
    print(f"Error importing Alpaca modules: {e}")
    sys.exit(1)

def test_market_data():
    """Test fetching real market data"""
    print("🔍 Testing Alpaca API connection...")
    
    try:
        client = StockHistoricalDataClient(
            os.getenv('ALPACA_API_KEY'), 
            os.getenv('ALPACA_SECRET_KEY')
        )
        
        # Test with a few popular stocks
        symbols = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'GOOGL']
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)  # Just last 5 days for quick test
        
        print(f"📊 Fetching data for {symbols} from {start_date.date()} to {end_date.date()}")
        
        request = StockBarsRequest(
            symbol_or_symbols=symbols,
            timeframe=TimeFrame.Day,
            start=start_date,
            end=end_date
        )
        
        bars = client.get_stock_bars(request)
        
        print(f"📊 BarSet type: {type(bars)}")
        print(f"📊 BarSet data: {bars}")
        
        if not bars:
            print("❌ No data received")
            return
            
        print(f"✅ Successfully fetched data")
        
        # Try to iterate through the BarSet
        try:
            for symbol, symbol_bars in bars.items():
                print(f"📈 {symbol}: {len(symbol_bars)} bars")
                if symbol_bars:
                    latest = symbol_bars[-1]
                    print(f"   Latest: ${latest.close:.2f} (Volume: {latest.volume:,})")
        except Exception as e:
            print(f"❌ Error iterating BarSet: {e}")
            print(f"📊 BarSet contents: {list(bars)}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_market_data()
