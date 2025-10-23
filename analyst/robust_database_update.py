#!/usr/bin/env python3
"""
Robust Database Update - Enhanced version with better error handling and monitoring
Prevents getting stuck by having comprehensive error handling and fallback mechanisms
"""
import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import time
from typing import List, Dict, Optional, Tuple

# Load environment variables
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / "config" / "api_keys.env"
    if env_file.exists():
        load_dotenv(env_file)
        print("🔑 Loaded API keys from .env file")
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
    print(f"❌ Error importing Alpaca modules: {e}")
    sys.exit(1)

class RobustDatabaseUpdater:
    """Robust database updater with comprehensive error handling"""
    
    def __init__(self):
        self.db_path = Path(__file__).parent / "nasdaq_db" / "nasdaq_90day.db"
        self.log_file = Path(__file__).parent / "logs" / "robust_update.log"
        self.log_file.parent.mkdir(exist_ok=True)
        
        # Configuration
        self.max_retries = 3
        self.batch_size = 50
        self.max_api_errors = 10
        self.min_success_rate = 0.8  # 80% success rate required
        
    def log(self, message: str, level: str = "INFO"):
        """Log message to file and console"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {level}: {message}\n"
        
        with open(self.log_file, 'a') as f:
            f.write(log_entry)
        
        print(f"{'🔴' if level == 'ERROR' else '🟡' if level == 'WARNING' else '🔵'} {message}")
    
    def get_database_status(self) -> Dict:
        """Get current database status"""
        if not self.db_path.exists():
            return {"status": "missing", "trading_days": 0, "last_date": None}
        
        try:
            conn = sqlite3.connect(self.db_path)
            result = conn.execute("""
                SELECT 
                    MIN(date) as start_date, 
                    MAX(date) as end_date, 
                    COUNT(DISTINCT date) as trading_days,
                    COUNT(*) as total_records
                FROM nasdaq_prices
            """).fetchone()
            conn.close()
            
            return {
                "status": "exists",
                "start_date": result[0],
                "end_date": result[1],
                "trading_days": result[2],
                "total_records": result[3]
            }
        except Exception as e:
            self.log(f"Database status check failed: {e}", "ERROR")
            return {"status": "error", "error": str(e)}
    
    def get_symbols(self) -> List[str]:
        """Get list of symbols from database"""
        if not self.db_path.exists():
            self.log("Database not found, cannot get symbols", "ERROR")
            return []
        
        try:
            conn = sqlite3.connect(self.db_path)
            symbols_df = pd.read_sql_query("SELECT DISTINCT symbol FROM nasdaq_prices ORDER BY symbol", conn)
            conn.close()
            return symbols_df['symbol'].tolist()
        except Exception as e:
            self.log(f"Failed to get symbols: {e}", "ERROR")
            return []
    
    def create_alpaca_client(self) -> Optional[StockHistoricalDataClient]:
        """Create Alpaca client with error handling"""
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        if not api_key or not secret_key:
            self.log("No Alpaca API keys found", "ERROR")
            return None
        
        try:
            client = StockHistoricalDataClient(api_key, secret_key)
            self.log("Alpaca client created successfully")
            return client
        except Exception as e:
            self.log(f"Failed to create Alpaca client: {e}", "ERROR")
            return None
    
    def fetch_batch_data(self, client: StockHistoricalDataClient, symbols: List[str], 
                        target_date: datetime) -> List[Dict]:
        """Fetch data for a batch of symbols with comprehensive error handling"""
        
        batch_data = []
        api_errors = 0
        
        # Try multiple date ranges
        date_ranges = [
            (target_date, target_date),  # Exact date
            (target_date - timedelta(days=1), target_date + timedelta(days=1)),  # ±1 day
            (target_date - timedelta(days=2), target_date + timedelta(days=2)),  # ±2 days
        ]
        
        for start_date, end_date in date_ranges:
            try:
                request = StockBarsRequest(
                    symbol_or_symbols=symbols,
                    timeframe=TimeFrame.Day,
                    start=start_date,
                    end=end_date
                )
                
                bars = client.get_stock_bars(request)
                
                if bars and bars.data:
                    for symbol, symbol_bars in bars.data.items():
                        if symbol_bars:
                            # Find closest bar to target date
                            target_date_only = target_date.date()
                            closest_bar = None
                            min_diff = float('inf')
                            
                            for bar in symbol_bars:
                                bar_date = bar.timestamp.date()
                                diff = abs((bar_date - target_date_only).days)
                                if diff < min_diff:
                                    min_diff = diff
                                    closest_bar = bar
                            
                            if closest_bar and min_diff <= 1:  # Within 1 day
                                batch_data.append({
                                    'symbol': symbol,
                                    'date': target_date_only.strftime('%Y-%m-%d'),
                                    'open': float(closest_bar.open),
                                    'high': float(closest_bar.high),
                                    'low': float(closest_bar.low),
                                    'close': float(closest_bar.close),
                                    'volume': float(closest_bar.volume),
                                    'adjusted_close': float(closest_bar.close)
                                })
                    
                    if batch_data:
                        break  # Found data, stop trying other ranges
                        
            except Exception as e:
                api_errors += 1
                self.log(f"API error for date range {start_date} to {end_date}: {e}", "WARNING")
                
                if api_errors >= self.max_api_errors:
                    self.log(f"Too many API errors ({api_errors}), stopping batch", "ERROR")
                    break
                
                time.sleep(1)  # Brief pause before retry
                continue
        
        return batch_data
    
    def update_database(self, new_data: List[Dict], target_date: str) -> bool:
        """Update database with new data"""
        if not new_data:
            self.log("No new data to update", "WARNING")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get existing data for technical indicators
            existing_df = pd.read_sql_query("SELECT * FROM nasdaq_prices ORDER BY symbol, date", conn)
            
            # Add new data
            new_df = pd.DataFrame(new_data)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df = combined_df.sort_values(['symbol', 'date'])
            
            # Calculate technical indicators
            updated_df = self.calculate_technical_indicators(combined_df, target_date)
            
            # Insert new records
            new_records = updated_df[updated_df['date'] == target_date]
            
            if not new_records.empty:
                new_records.to_sql('nasdaq_prices', conn, if_exists='append', index=False)
                self.log(f"Added {len(new_records)} records for {target_date}")
            
            # Remove oldest day to maintain 90-day window
            self.remove_oldest_day(conn)
            
            conn.close()
            return True
            
        except Exception as e:
            self.log(f"Database update failed: {e}", "ERROR")
            return False
    
    def calculate_technical_indicators(self, df: pd.DataFrame, target_date: str) -> pd.DataFrame:
        """Calculate technical indicators for target date"""
        target_df = df[df['date'] == target_date].copy()
        
        if target_df.empty:
            return df
        
        for symbol in target_df['symbol'].unique():
            symbol_data = df[df['symbol'] == symbol].sort_values('date')
            
            if len(symbol_data) < 20:
                continue
            
            target_idx = target_df[target_df['symbol'] == symbol].index[0]
            
            # Calculate RSI
            if len(symbol_data) >= 14:
                rsi = self.calculate_rsi(symbol_data['close'].values, 14)
                if len(rsi) > 0:
                    df.loc[target_idx, 'rsi'] = rsi[-1]
            
            # Calculate ATR
            if len(symbol_data) >= 14:
                atr = self.calculate_atr(symbol_data[['high', 'low', 'close']].values, 14)
                if len(atr) > 0:
                    df.loc[target_idx, 'atr'] = atr[-1]
            
            # Calculate Z-Score
            if len(symbol_data) >= 20:
                z_score = self.calculate_z_score(symbol_data['close'].values, 20)
                if len(z_score) > 0:
                    df.loc[target_idx, 'z_score'] = z_score[-1]
            
            # Calculate ADR
            if len(symbol_data) >= 20:
                adr = self.calculate_adr_pct(symbol_data[['high', 'low', 'close']].values, 20)
                if len(adr) > 0:
                    df.loc[target_idx, 'adr_pct'] = adr[-1]
        
        return df
    
    def remove_oldest_day(self, conn: sqlite3.Connection):
        """Remove oldest day to maintain 90-day window"""
        try:
            oldest_date = conn.execute("SELECT MIN(date) FROM nasdaq_prices").fetchone()[0]
            count_before = conn.execute("SELECT COUNT(*) FROM nasdaq_prices").fetchone()[0]
            
            conn.execute("DELETE FROM nasdaq_prices WHERE date = ?", (oldest_date,))
            
            count_after = conn.execute("SELECT COUNT(*) FROM nasdaq_prices").fetchone()[0]
            deleted_count = count_before - count_after
            
            if deleted_count > 0:
                self.log(f"Removed {deleted_count} records from {oldest_date}")
                
        except Exception as e:
            self.log(f"Failed to remove oldest day: {e}", "WARNING")
    
    def calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return np.array([])
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        rsi = np.zeros(len(prices) - period)
        
        for i in range(period, len(prices)):
            if avg_loss == 0:
                rsi[i - period] = 100
            else:
                rs = avg_gain / avg_loss
                rsi[i - period] = 100 - (100 / (1 + rs))
            
            if i < len(prices) - 1:
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        return rsi
    
    def calculate_atr(self, hlc: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate ATR indicator"""
        if len(hlc) < period + 1:
            return np.array([])
        
        high, low, close = hlc[:, 0], hlc[:, 1], hlc[:, 2]
        
        tr = np.maximum(high[1:] - low[1:], 
                       np.maximum(np.abs(high[1:] - close[:-1]), 
                                 np.abs(low[1:] - close[:-1])))
        
        atr = np.zeros(len(tr) - period + 1)
        atr[0] = np.mean(tr[:period])
        
        for i in range(1, len(atr)):
            atr[i] = (atr[i-1] * (period - 1) + tr[period + i - 1]) / period
        
        return atr
    
    def calculate_z_score(self, prices: np.ndarray, period: int = 20) -> np.ndarray:
        """Calculate Z-Score indicator"""
        if len(prices) < period:
            return np.array([])
        
        z_scores = np.zeros(len(prices) - period + 1)
        
        for i in range(period - 1, len(prices)):
            window = prices[i - period + 1:i + 1]
            mean = np.mean(window)
            std = np.std(window)
            
            if std > 0:
                z_scores[i - period + 1] = (prices[i] - mean) / std
            else:
                z_scores[i - period + 1] = 0
        
        return z_scores
    
    def calculate_adr_pct(self, hlc: np.ndarray, period: int = 20) -> np.ndarray:
        """Calculate ADR percentage indicator"""
        if len(hlc) < period:
            return np.array([])
        
        high, low, close = hlc[:, 0], hlc[:, 1], hlc[:, 2]
        
        adr_pct = np.zeros(len(hlc) - period + 1)
        
        for i in range(period - 1, len(hlc)):
            window_high = high[i - period + 1:i + 1]
            window_low = low[i - period + 1:i + 1]
            window_close = close[i - period + 1:i + 1]
            
            daily_ranges = (window_high - window_low) / window_close
            adr_pct[i - period + 1] = np.mean(daily_ranges) * 100
        
        return adr_pct
    
    def run_update(self) -> bool:
        """Run the complete database update process"""
        
        self.log("Starting robust database update")
        
        # Check database status
        db_status = self.get_database_status()
        if db_status["status"] != "exists":
            self.log(f"Database issue: {db_status}", "ERROR")
            return False
        
        self.log(f"Database status: {db_status['start_date']} to {db_status['end_date']} ({db_status['trading_days']} days)")
        
        # Determine target date
        if db_status["end_date"]:
            last_date = datetime.strptime(db_status["end_date"], '%Y-%m-%d')
        else:
            last_date = datetime.now() - timedelta(days=30)
        
        target_date = last_date + timedelta(days=1)
        while target_date.weekday() >= 5:  # Skip weekends
            target_date += timedelta(days=1)
        
        self.log(f"Target date: {target_date.strftime('%Y-%m-%d')}")
        
        # Get symbols
        symbols = self.get_symbols()
        if not symbols:
            self.log("No symbols found", "ERROR")
            return False
        
        self.log(f"Processing {len(symbols)} symbols")
        
        # Create Alpaca client
        client = self.create_alpaca_client()
        if not client:
            return False
        
        # Fetch data in batches
        all_data = []
        successful_batches = 0
        total_batches = (len(symbols) + self.batch_size - 1) // self.batch_size
        
        for i in range(0, len(symbols), self.batch_size):
            batch_symbols = symbols[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            
            self.log(f"Processing batch {batch_num}/{total_batches} ({len(batch_symbols)} symbols)")
            
            batch_data = self.fetch_batch_data(client, batch_symbols, target_date)
            
            if batch_data:
                all_data.extend(batch_data)
                successful_batches += 1
                self.log(f"Batch {batch_num}: {len(batch_data)} records")
            else:
                self.log(f"Batch {batch_num}: No data found", "WARNING")
        
        # Check success rate
        success_rate = successful_batches / total_batches
        if success_rate < self.min_success_rate:
            self.log(f"Success rate too low: {success_rate:.2%} < {self.min_success_rate:.2%}", "ERROR")
            return False
        
        self.log(f"Success rate: {success_rate:.2%} ({successful_batches}/{total_batches} batches)")
        
        # Update database
        if all_data:
            success = self.update_database(all_data, target_date.strftime('%Y-%m-%d'))
            if success:
                self.log(f"Database update completed successfully with {len(all_data)} records")
                return True
            else:
                self.log("Database update failed", "ERROR")
                return False
        else:
            self.log("No data fetched, skipping update", "WARNING")
            return False

def main():
    """Main function"""
    updater = RobustDatabaseUpdater()
    success = updater.run_update()
    
    if success:
        print("✅ Database update completed successfully")
    else:
        print("❌ Database update failed")
        sys.exit(1)

if __name__ == "__main__":
    main()

