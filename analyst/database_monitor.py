#!/usr/bin/env python3
"""
Database Monitor - Health check and alerting for NASDAQ database
Prevents getting stuck by monitoring database health and data freshness
"""
import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, List, Optional

# Load environment variables
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / "config" / "api_keys.env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

def check_database_health() -> Dict:
    """Check database health and return status"""
    
    db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq_90day.db"
    
    if not db_path.exists():
        return {
            "status": "ERROR",
            "message": "Database file not found",
            "action": "Run database initialization"
        }
    
    try:
        conn = sqlite3.connect(db_path)
        
        # Check basic stats
        result = conn.execute("""
            SELECT 
                MIN(date) as start_date, 
                MAX(date) as end_date, 
                COUNT(DISTINCT date) as trading_days,
                COUNT(*) as total_records,
                COUNT(DISTINCT symbol) as unique_symbols
            FROM nasdaq_prices
        """).fetchone()
        
        start_date, end_date, trading_days, total_records, unique_symbols = result
        
        # Check data freshness
        today = datetime.now().date()
        if end_date:
            last_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            days_behind = (today - last_date).days
        else:
            days_behind = 999
        
        # Check for missing recent data
        recent_dates = []
        if end_date:
            last_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            for i in range(1, 8):  # Check last 7 days
                check_date = last_date_obj + timedelta(days=i)
                if check_date.weekday() < 5:  # Weekdays only
                    recent_dates.append(check_date.strftime('%Y-%m-%d'))
        
        # Check if recent dates have data
        missing_dates = []
        for date_str in recent_dates:
            count = conn.execute("SELECT COUNT(*) FROM nasdaq_prices WHERE date = ?", (date_str,)).fetchone()[0]
            if count == 0:
                missing_dates.append(date_str)
        
        conn.close()
        
        # Determine status
        if days_behind > 3:
            status = "CRITICAL"
            message = f"Database is {days_behind} days behind"
            action = "Run update_database_mcp.py immediately"
        elif days_behind > 1:
            status = "WARNING"
            message = f"Database is {days_behind} days behind"
            action = "Run update_database_mcp.py"
        elif missing_dates:
            status = "WARNING"
            message = f"Missing data for dates: {', '.join(missing_dates)}"
            action = "Run update_database_mcp.py"
        else:
            status = "HEALTHY"
            message = "Database is up to date"
            action = "No action needed"
        
        return {
            "status": status,
            "message": message,
            "action": action,
            "stats": {
                "start_date": start_date,
                "end_date": end_date,
                "trading_days": trading_days,
                "total_records": total_records,
                "unique_symbols": unique_symbols,
                "days_behind": days_behind,
                "missing_dates": missing_dates
            }
        }
        
    except Exception as e:
        return {
            "status": "ERROR",
            "message": f"Database error: {e}",
            "action": "Check database integrity"
        }

def send_alert(status: str, message: str, action: str):
    """Send alert (for now, just log to file)"""
    
    log_file = Path(__file__).parent / "logs" / "database_monitor.log"
    log_file.parent.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    alert = f"[{timestamp}] {status}: {message} | Action: {action}\n"
    
    with open(log_file, 'a') as f:
        f.write(alert)
    
    print(f"🚨 {status}: {message}")
    print(f"💡 Action: {action}")

def main():
    """Main monitoring function"""
    
    print("🔍 Database Health Check")
    print("=" * 40)
    
    health = check_database_health()
    
    print(f"Status: {health['status']}")
    print(f"Message: {health['message']}")
    print(f"Action: {health['action']}")
    
    if 'stats' in health:
        stats = health['stats']
        print(f"\n📊 Database Stats:")
        print(f"  Date Range: {stats['start_date']} to {stats['end_date']}")
        print(f"  Trading Days: {stats['trading_days']}")
        print(f"  Total Records: {stats['total_records']:,}")
        print(f"  Unique Symbols: {stats['unique_symbols']}")
        print(f"  Days Behind: {stats['days_behind']}")
        
        if stats['missing_dates']:
            print(f"  Missing Dates: {', '.join(stats['missing_dates'])}")
    
    # Send alert if not healthy
    if health['status'] in ['CRITICAL', 'WARNING', 'ERROR']:
        send_alert(health['status'], health['message'], health['action'])
    
    return health['status'] in ['HEALTHY']

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

