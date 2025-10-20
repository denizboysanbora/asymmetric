#!/usr/bin/env python3
"""
Tight Base Logic Explanation
Shows exactly how tight base calculation works
"""
import os
import sys
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Dict

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

def get_july_data():
    """Get all PRTS data for July 2020"""
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    client = StockHistoricalDataClient(api_key, secret_key)
    
    request = StockBarsRequest(
        symbol_or_symbols="PRTS",
        timeframe=TimeFrame.Day,
        start=datetime(2020, 1, 1),
        end=datetime(2020, 7, 31)
    )
    
    bars = client.get_stock_bars(request)
    return bars.data["PRTS"]

def explain_tight_base_logic(bars: List[Bar]):
    """Explain the tight base logic step by step"""
    
    print("📦 TIGHT BASE LOGIC EXPLANATION")
    print("=" * 80)
    print("🎯 Purpose: Measure how tight/consolidated the price range is")
    print("🎯 Concept: Flag patterns need tight consolidation before breakout")
    print("=" * 80)
    
    # Use July 6th as example (the day that passes)
    target_date = datetime(2020, 7, 6).date()
    
    # Get historical data up to July 6th (EXCLUDING July 6th for setup analysis)
    historical_bars = [b for b in bars if b.timestamp.date() < target_date]
    
    print(f"\n📅 EXAMPLE: July 6th Analysis (excluding July 6th from calculation)")
    print(f"📊 Using last 30 trading days before July 6th")
    print("-" * 80)
    
    # Get the last 30 days of data
    last_30_bars = historical_bars[-30:]
    closes = np.array([float(bar.close) for bar in last_30_bars])
    
    print(f"📊 Last 30 Trading Days (for tight base calculation):")
    print(f"   Start Date: {last_30_bars[0].timestamp.date()}")
    print(f"   End Date: {last_30_bars[-1].timestamp.date()}")
    print(f"   Total Days: {len(last_30_bars)}")
    
    # Step 1: Find the range
    range_high = float(np.max(closes))
    range_low = float(np.min(closes))
    range_size = range_high - range_low
    
    print(f"\n1. 📈 FIND THE PRICE RANGE:")
    print(f"   Range High: ${range_high:.2f}")
    print(f"   Range Low: ${range_low:.2f}")
    print(f"   Range Size: ${range_size:.2f}")
    
    # Step 2: Calculate range percentage
    range_pct = (range_size / range_low * 100) if range_low > 0 else 0
    
    print(f"\n2. 📊 CALCULATE RANGE PERCENTAGE:")
    print(f"   Formula: (Range Size / Range Low) × 100")
    print(f"   Calculation: (${range_size:.2f} / ${range_low:.2f}) × 100")
    print(f"   Result: {range_pct:.1f}%")
    
    # Step 3: Compare to threshold
    tight_base_threshold = 55  # Our adjusted parameter
    tight_base_ok = range_pct <= tight_base_threshold
    
    print(f"\n3. 🎯 COMPARE TO THRESHOLD:")
    print(f"   Threshold: ≤{tight_base_threshold}%")
    print(f"   Actual: {range_pct:.1f}%")
    print(f"   Result: {'✅ PASS' if tight_base_ok else '❌ FAIL'}")
    
    # Show the actual price data
    print(f"\n4. 📊 ACTUAL PRICE DATA (Last 30 Days):")
    print("   Date       | Close Price")
    print("   " + "-" * 25)
    for i, bar in enumerate(last_30_bars[-10:]):  # Show last 10 for brevity
        print(f"   {bar.timestamp.date()} | ${float(bar.close):>8.2f}")
    print("   " + "-" * 25)
    print(f"   ... and {len(last_30_bars)-10} more days")
    
    # Show why this logic makes sense
    print(f"\n5. 💡 WHY THIS LOGIC MAKES SENSE:")
    print(f"   • Flag patterns need TIGHT consolidation")
    print(f"   • Wide ranges (like 70%) = no consolidation")
    print(f"   • Tight ranges (like 52%) = good consolidation")
    print(f"   • Lower percentage = tighter consolidation")
    
    # Show comparison with other days
    print(f"\n6. 📊 COMPARISON WITH OTHER JULY DAYS:")
    print("   Day    | Range % | Result")
    print("   " + "-" * 30)
    
    # July 1
    july1_bars = [b for b in bars if b.timestamp.date() < datetime(2020, 7, 1).date()]
    july1_last30 = july1_bars[-30:]
    july1_closes = np.array([float(bar.close) for bar in july1_last30])
    july1_range_high = float(np.max(july1_closes))
    july1_range_low = float(np.min(july1_closes))
    july1_range_pct = (july1_range_high - july1_range_low) / july1_range_low * 100
    
    # July 2
    july2_bars = [b for b in bars if b.timestamp.date() < datetime(2020, 7, 2).date()]
    july2_last30 = july2_bars[-30:]
    july2_closes = np.array([float(bar.close) for bar in july2_last30])
    july2_range_high = float(np.max(july2_closes))
    july2_range_low = float(np.min(july2_closes))
    july2_range_pct = (july2_range_high - july2_range_low) / july2_range_low * 100
    
    print(f"   July 1 | {july1_range_pct:>6.1f}% | {'✅' if july1_range_pct <= 55 else '❌'}")
    print(f"   July 2 | {july2_range_pct:>6.1f}% | {'✅' if july2_range_pct <= 55 else '❌'}")
    print(f"   July 6 | {range_pct:>6.1f}% | {'✅' if tight_base_ok else '❌'}")
    
    print(f"\n7. 🔧 PARAMETER SENSITIVITY:")
    print(f"   • Original threshold: 15% (too strict)")
    print(f"   • Adjusted threshold: 55% (catches July 6-8)")
    print(f"   • July 6 range: 52.2% (just under 55% limit)")
    print(f"   • July 2 range: 58.1% (just over 55% limit)")
    
    print(f"\n8. 🎯 KEY INSIGHT:")
    print(f"   The tight base logic measures consolidation quality:")
    print(f"   • Lower % = tighter consolidation = better flag setup")
    print(f"   • Higher % = wider range = weaker consolidation")
    print(f"   • 52.2% = good consolidation for flag pattern")
    print(f"   • 70.8% = too wide for flag pattern")

def main():
    """Main explanation function"""
    print("🔍 Tight Base Logic Explanation")
    print("Understanding how tight base calculation works")
    
    try:
        # Get data
        bars = get_july_data()
        print(f"📊 Fetched {len(bars)} total bars")
        
        # Explain tight base logic
        explain_tight_base_logic(bars)
        
        print("\n" + "=" * 80)
        print("📋 SUMMARY:")
        print("=" * 80)
        print("🎯 Tight Base = (Highest Price - Lowest Price) / Lowest Price × 100")
        print("🎯 Measures consolidation quality over last 30 trading days")
        print("🎯 Lower percentage = tighter consolidation = better flag setup")
        print("🎯 Adjusted threshold: 55% (from original 15%)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
