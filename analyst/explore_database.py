#!/usr/bin/env python3
"""
Explore the NASDAQ test database
"""
import sqlite3
import pandas as pd
from datetime import datetime

def explore_database():
    """Explore the NASDAQ database"""
    conn = sqlite3.connect("nasdaq_2025.db")
    
    print("🗄️ NASDAQ Test Database Explorer")
    print("=" * 50)
    
    # Show basic stats
    stats = pd.read_sql("""
        SELECT 
            COUNT(*) as total_records,
            MIN(date) as first_date,
            MAX(date) as last_date,
            COUNT(DISTINCT symbol) as unique_symbols
        FROM nasdaq_prices
    """, conn)
    
    print("📊 Database Overview:")
    print(f"Total records: {stats.iloc[0]['total_records']}")
    print(f"Date range: {stats.iloc[0]['first_date']} to {stats.iloc[0]['last_date']}")
    print(f"Unique symbols: {stats.iloc[0]['unique_symbols']}")
    
    # Show price analysis
    price_stats = pd.read_sql("""
        SELECT 
            MIN(close) as min_price,
            MAX(close) as max_price,
            AVG(close) as avg_price,
            MIN(rsi) as min_rsi,
            MAX(rsi) as max_rsi,
            AVG(rsi) as avg_rsi
        FROM nasdaq_prices
    """, conn)
    
    print(f"\n💰 Price Analysis:")
    print(f"Price range: ${price_stats.iloc[0]['min_price']:.2f} - ${price_stats.iloc[0]['max_price']:.2f}")
    print(f"Average price: ${price_stats.iloc[0]['avg_price']:.2f}")
    print(f"RSI range: {price_stats.iloc[0]['min_rsi']:.1f} - {price_stats.iloc[0]['max_rsi']:.1f}")
    print(f"Average RSI: {price_stats.iloc[0]['avg_rsi']:.1f}")
    
    # Show latest data
    latest = pd.read_sql("""
        SELECT date, close, volume, rsi, atr
        FROM nasdaq_prices 
        ORDER BY date DESC 
        LIMIT 10
    """, conn)
    
    print(f"\n📈 Latest 10 Records:")
    print(latest.to_string(index=False))
    
    # Show monthly summary
    monthly = pd.read_sql("""
        SELECT 
            strftime('%Y-%m', date) as month,
            COUNT(*) as trading_days,
            MIN(close) as min_price,
            MAX(close) as max_price,
            AVG(close) as avg_price,
            AVG(rsi) as avg_rsi
        FROM nasdaq_prices 
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month
    """, conn)
    
    print(f"\n📅 Monthly Summary:")
    print(monthly.to_string(index=False))
    
    # Export to CSV for Excel
    print(f"\n📊 Exporting to CSV for Excel...")
    all_data = pd.read_sql("SELECT * FROM nasdaq_prices ORDER BY date", conn)
    all_data.to_csv("aapl_2025.csv", index=False)
    print("✅ CSV file created: aapl_2025.csv")
    
    conn.close()

def show_sample_queries():
    """Show sample SQL queries for the database"""
    print(f"\n🔍 Sample SQL Queries:")
    print("=" * 30)
    
    queries = [
        ("Get all data", "SELECT * FROM nasdaq_prices LIMIT 10;"),
        ("Get latest price", "SELECT * FROM nasdaq_prices ORDER BY date DESC LIMIT 1;"),
        ("Get RSI > 70 (overbought)", "SELECT date, close, rsi FROM nasdaq_prices WHERE rsi > 70;"),
        ("Get RSI < 30 (oversold)", "SELECT date, close, rsi FROM nasdaq_prices WHERE rsi < 30;"),
        ("Get highest volume days", "SELECT date, close, volume FROM nasdaq_prices ORDER BY volume DESC LIMIT 10;"),
        ("Get price changes", "SELECT date, close, LAG(close) OVER (ORDER BY date) as prev_close, close - LAG(close) OVER (ORDER BY date) as change FROM nasdaq_prices;"),
        ("Get monthly averages", "SELECT strftime('%Y-%m', date) as month, AVG(close) as avg_price, AVG(rsi) as avg_rsi FROM nasdaq_prices GROUP BY month ORDER BY month;")
    ]
    
    for name, query in queries:
        print(f"\n{name}:")
        print(f"  {query}")

if __name__ == "__main__":
    explore_database()
    show_sample_queries()
