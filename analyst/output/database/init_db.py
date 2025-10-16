#!/usr/bin/env python3
"""
Initialize signals database for Trader agent.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'signals.db')

def init_database():
    """Create database schema with indexes."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create signals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT (datetime('now','localtime')),
            symbol TEXT NOT NULL,
            price REAL NOT NULL,
            change_pct REAL NOT NULL,
            tr_atr REAL NOT NULL,
            z_score REAL NOT NULL,
            signal_type TEXT NOT NULL,
            asset_class TEXT NOT NULL
        )
    """)
    
    # Create indexes for fast queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp 
        ON signals(timestamp DESC)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_symbol 
        ON signals(symbol)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_asset_class 
        ON signals(asset_class)
    """)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_database()


