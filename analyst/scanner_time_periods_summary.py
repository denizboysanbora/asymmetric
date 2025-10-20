#!/usr/bin/env python3
"""
Breakout Scanner Time Periods Summary
Shows the different time periods and lookback windows used in the scanners
"""
import pandas as pd

def create_time_periods_summary():
    """Create a summary table of scanner time periods"""
    
    # Define the time periods
    periods = [
        ("Minimum Data Required", "60 days", "60 days", "Both require 60+ days of historical data"),
        ("Base Analysis Window", "20 days", "20 days", "Recent price consolidation analysis"),
        ("Prior Impulse Detection", "60 days", "N/A", "Flag: 30%+ move in last 60 days, Range: No impulse required"),
        ("Impulse Window Size", "40 days", "N/A", "20-day windows within 60-day lookback for Flag"),
        ("ATR Calculation Period", "14 days", "14 days", "Average True Range calculation"),
        ("ATR Moving Average", "50 days", "50 days", "ATR smoothed over 50 days"),
        ("Volume Moving Average", "50 days", "50 days", "Volume smoothed over 50 days"),
        ("Higher Lows Analysis", "20 days", "20 days", "Pattern detection within base window"),
        ("Market Filter", "10/20 days", "10/20 days", "Benchmark 10DMA vs 20DMA comparison"),
        ("Relative Strength", "50 days", "50 days", "Price/benchmark vs 50-day RS average"),
        ("Total Lookback", "~110 days", "~90 days", "Maximum historical data needed"),
        ("Effective Analysis", "~3.5 months", "~3 months", "Rough estimate for sufficient data")
    ]
    
    # Create DataFrame
    df = pd.DataFrame(periods, columns=[
        "Time Period", 
        "Flag Breakout", 
        "Range Breakout", 
        "Description"
    ])
    
    print("⏰ BREAKOUT SCANNER TIME PERIODS SUMMARY")
    print("=" * 100)
    print()
    
    # Print the table
    print(df.to_string(index=False))
    
    print()
    print("=" * 100)
    print("📊 KEY INSIGHTS:")
    print("=" * 100)
    print("1. 🕐 Minimum Requirement: Both scanners need 60+ days of data")
    print("2. 📏 Base Analysis: Both use 20-day windows for recent price action")
    print("3. 🚩 Prior Impulse: Only Flag breakout requires 30%+ move in last 60 days")
    print("4. 📊 Technical Indicators: ATR and Volume use 50-day moving averages")
    print("5. 🎯 Total Lookback: Scanners need ~3-3.5 months of historical data")
    print()
    
    print("🔍 WHY NASDAQ OCTOBER ANALYSIS FOUND NO BREAKOUTS:")
    print("- October database: 13 trading days (Oct 1-17, 2025)")
    print("- Combined Aug-Sep-Oct: ~55 trading days")
    print("- Required minimum: 60+ trading days")
    print("- Result: Insufficient data for proper breakout analysis")
    print()
    
    print("💡 RECOMMENDATIONS:")
    print("1. 📅 Use databases with 3+ months of data for reliable analysis")
    print("2. 🔧 For shorter periods, create relaxed parameters")
    print("3. 📊 Focus on pattern recognition rather than strict breakout criteria")
    print("4. 🎯 Consider momentum analysis for limited data scenarios")

if __name__ == "__main__":
    create_time_periods_summary()
