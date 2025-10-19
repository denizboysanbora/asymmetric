#!/usr/bin/env python3
"""
Unified Analyst - Consolidated Breakout Detection and Trading System
Combines all analyst functionality into a single, powerful script.

Usage:
    python analyst.py --mode breakout --scan
    python analyst.py --mode advanced --daemon
    python analyst.py --mode mcp --auto-trade
"""
import os
import sys
import json
import argparse
import subprocess
import numpy as np
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from pydantic import BaseModel, Field
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables first
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent / "config" / "api_keys.env"
    if env_file.exists():
        load_dotenv(env_file)
        print("🔑 Loaded API keys from .env file", file=sys.stderr)
except ImportError:
    pass

# Add alpaca directory to path
ALPACA_DIR = Path(__file__).parent / "input" / "alpaca"
sys.path.insert(0, str(ALPACA_DIR))

# Import Alpaca modules
try:
    from alpaca.data.historical import ScreenerClient, StockHistoricalDataClient
    from alpaca.data.requests import (
        MarketMoversRequest,
        MostActivesRequest,
        StockBarsRequest,
        StockSnapshotRequest,
    )
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.enums import MarketType, MostActivesBy
    from alpaca.trading.requests import GetAssetsRequest
    from alpaca.trading.enums import AssetClass, AssetExchange, AssetStatus
    from alpaca.trading.client import TradingClient
    from alpaca.data.models import Bar
except ImportError as e:
    print(f"Error importing Alpaca modules: {e}", file=sys.stderr)
    sys.exit(1)

class SetupTag(BaseModel):
    """Setup tag model."""
    setup: str = Field(..., description="Setup type")
    triggered: bool = Field(..., description="Whether setup is triggered")
    score: float = Field(..., description="Setup strength score (0-1)")
    meta: Dict = Field(default_factory=dict, description="Setup-specific metadata")
    
    model_config = {"extra": "allow"}

class AnalystConfig:
    """Unified analyst configuration"""
    
    # Operating hours
    SCHEDULE_START = 10  # 10 AM ET
    SCHEDULE_END = 17    # 5 PM ET (includes 4:00 PM scan)
    
    # Email settings
    EMAIL_RECIPIENT = "deniz@bora.box"
    EMAIL_SUBJECT = "Flag Breakout Signal"
    
    # Trading parameters
    MAX_POSITION_SIZE = 0.1  # 10% of portfolio per position
    STOP_LOSS_PCT = 0.05     # 5% stop loss
    TAKE_PROFIT_PCT = 0.15   # 15% take profit
    
    # Scanning parameters
    MIN_PRICE = 1.0
    MAX_PRICE = 1000.0
    MIN_DAILY_VOLUME = 100000
    
    # Technical indicators
    RSI_PERIOD = 14
    ATR_PERIOD = 14
    Z_SCORE_PERIOD = 20
    ADR_PERIOD = 20

class UnifiedAnalyst:
    """Unified analyst combining all functionality"""
    
    def __init__(self, mode="breakout", use_mcp=False, auto_trade=False):
        self.mode = mode
        self.use_mcp = use_mcp
        self.auto_trade = auto_trade
        
        # API credentials
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        if not self.api_key or not self.secret_key:
            print("❌ ALPACA_API_KEY and ALPACA_SECRET_KEY not set", file=sys.stderr)
            sys.exit(1)
        
        # Initialize clients
        self.trading_client = TradingClient(self.api_key, self.secret_key, paper=True)
        self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)
        
        # Configuration
        self.config = AnalystConfig()
        # Database path
        self.db_path = str(Path(__file__).parent / "nasdaq_2025.db")
        
        # State
        self.portfolio_state_file = Path(__file__).parent / "portfolio_state.json"
        self.portfolio = self.load_portfolio_state()
        
        print(f"Unified Analyst initialized", file=sys.stderr)
        print(f"Mode: {mode}", file=sys.stderr)
        print(f"MCP: {'Enabled' if use_mcp else 'Disabled'}", file=sys.stderr)
        print(f"Auto-trade: {'Enabled' if auto_trade else 'Disabled'}", file=sys.stderr)
    
    def load_portfolio_state(self) -> Dict:
        """Load portfolio state from file"""
        if self.portfolio_state_file.exists():
            try:
                with open(self.portfolio_state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default portfolio state
        return {
            "cash": 100000.0,  # Starting with $100k
            "positions": {},
            "orders": [],
            "total_value": 100000.0,
            "last_updated": datetime.now().isoformat()
        }
    
    def save_portfolio_state(self):
        """Save portfolio state to file"""
        self.portfolio["last_updated"] = datetime.now().isoformat()
        with open(self.portfolio_state_file, 'w') as f:
            json.dump(self.portfolio, f, indent=2)
    
    def get_liquid_stocks(self) -> List[str]:
        """Get liquid stock universe using comprehensive filtering"""
        try:
            # Get all tradable assets
            asset_filter = GetAssetsRequest(
                status=AssetStatus.ACTIVE,
                asset_class=AssetClass.US_EQUITY,
            )
            assets = self.trading_client.get_all_assets(asset_filter)
            assets_by_symbol = {
                asset.symbol.upper(): asset
                for asset in assets
                if asset.tradable and asset.shortable and asset.status == AssetStatus.ACTIVE
            }
            
            # Apply basic filters
            candidate_symbols = []
            for symbol, asset in assets_by_symbol.items():
                if self._symbol_passes_basic_filters(symbol) and self._is_preferred_exchange(asset.exchange):
                    candidate_symbols.append(symbol)
            
            # Get snapshots for filtering
            symbols_to_snapshot = candidate_symbols
            snapshots = {}
            
            try:
                chunk_size = 150
                for i, chunk in enumerate(self._chunk(symbols_to_snapshot, chunk_size)):
                    response = self.data_client.get_stock_snapshot(
                        StockSnapshotRequest(symbol_or_symbols=chunk)
                    )
                    snapshots.update(response)
            except Exception as e:
                print(f"Snapshot retrieval failed: {e}", file=sys.stderr)
            
            # Filter by price and volume
            liquid_candidates = []
            for symbol in symbols_to_snapshot:
                snap = snapshots.get(symbol)
                daily_bar = getattr(snap, "daily_bar", None) if snap else None
                if not daily_bar:
                    continue
                
                close_price = float(getattr(daily_bar, "close", 0.0))
                daily_volume = float(getattr(daily_bar, "volume", 0.0))
                
                if (self.config.MIN_PRICE <= close_price <= self.config.MAX_PRICE and 
                    daily_volume >= self.config.MIN_DAILY_VOLUME):
                    liquid_candidates.append((symbol, daily_volume))
            
            # Sort by volume and return all symbols
            liquid_candidates.sort(key=lambda item: item[1], reverse=True)
            return [symbol for symbol, _ in liquid_candidates]
            
        except Exception as e:
            print(f"Error getting liquid stocks: {e}", file=sys.stderr)
            return []
    
    def _symbol_passes_basic_filters(self, symbol: str) -> bool:
        """Check if symbol passes basic filters"""
        upl = symbol.upper()
        if not (2 <= len(upl) <= 5):
            return False
        if upl.isdigit():
            return False
        if not upl.replace(".", "").replace("-", "").isalnum():
            return False
        
        disallowed_fragments = ["ETF", "FUND", "TRUST", "REIT", "UT", "CEF", "CLOSED"]
        if any(fragment in upl for fragment in disallowed_fragments):
            return False
        
        disallowed_suffixes = [".PR", ".PW", ".W", ".WS", ".WT"]
        if any(upl.endswith(suffix) for suffix in disallowed_suffixes):
            return False
        
        foreign_markers = [".TO", ".L", ".HK", ".SH", ".SZ"]
        if any(marker in upl for marker in foreign_markers):
            return False
        
        return True

    # --- Database helpers ---
    def _db_conn(self):
        return sqlite3.connect(self.db_path)

    def _db_latest_date(self) -> Optional[str]:
        try:
            with self._db_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT MAX(date) FROM nasdaq_prices")
                row = cur.fetchone()
                return row[0] if row and row[0] else None
        except Exception:
            return None

    def _db_get_recent_bars(self, symbol: str, num_days: int) -> Optional[pd.DataFrame]:
        try:
            latest = self._db_latest_date()
            if not latest:
                return None
            with self._db_conn() as conn:
                df = pd.read_sql(
                    """
                    SELECT date, open, high, low, close, volume
                    FROM nasdaq_prices
                    WHERE symbol = ? AND date <= ?
                    ORDER BY date DESC
                    LIMIT ?
                    """,
                    conn,
                    params=(symbol, latest, num_days),
                )
            if df.empty:
                return None
            df = df.sort_values("date").reset_index(drop=True)
            return df
        except Exception:
            return None

    def _db_get_benchmark_bars(self, symbol: str = "QQQ", num_days: int = 30) -> Optional[pd.DataFrame]:
        return self._db_get_recent_bars(symbol, num_days)

    def _db_upsert_row(self, row: dict) -> None:
        with self._db_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO nasdaq_prices
                (symbol, date, open, high, low, close, volume, adjusted_close, rsi, atr)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("symbol"), row.get("date"), row.get("open"), row.get("high"),
                    row.get("low"), row.get("close"), row.get("volume"), row.get("adjusted_close"),
                    row.get("rsi"), row.get("atr"),
                ),
            )
            conn.commit()

    def _db_insert_ignore_row(self, row: dict) -> None:
        """Insert if missing; do not overwrite existing rows."""
        with self._db_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR IGNORE INTO nasdaq_prices
                (symbol, date, open, high, low, close, volume, adjusted_close, rsi, atr)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("symbol"), row.get("date"), row.get("open"), row.get("high"),
                    row.get("low"), row.get("close"), row.get("volume"), row.get("adjusted_close"),
                    row.get("rsi"), row.get("atr"),
                ),
            )
            conn.commit()

    def _db_update_indicators_if_null(self, symbol: str, date: str, rsi: Optional[float], atr: Optional[float]) -> None:
        with self._db_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE nasdaq_prices
                SET rsi = COALESCE(rsi, ?), atr = COALESCE(atr, ?)
                WHERE symbol = ? AND date = ?
                """,
                (rsi, atr, symbol, date),
            )
            conn.commit()

    # --- Daily close database update ---
    def update_database_after_close(self) -> None:
        """Fetch today's daily bars for all NASDAQ symbols and upsert into SQLite.
        Uses Alpaca for the latest bar only; subsequent historical reads are from SQLite.
        """
        try:
            today = datetime.now().date()
            target_date = today

            symbols = self.get_liquid_stocks()
            if not symbols:
                print("No symbols to update in DB", file=sys.stderr)
                return

            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            from alpaca.data.enums import Adjustment

            updated = 0
            for chunk in self._chunk(symbols, 200):
                try:
                    req = StockBarsRequest(
                        symbol_or_symbols=chunk,
                        timeframe=TimeFrame.Day,
                        start=datetime.combine(target_date, datetime.min.time()),
                        end=datetime.combine(target_date, datetime.max.time()),
                        adjustment=Adjustment.ALL,
                        limit=10000,
                    )
                    resp = self.data_client.get_stock_bars(req)
                    if not resp or not hasattr(resp, "df") or resp.df is None or resp.df.empty:
                        continue
                    df = resp.df.reset_index()
                    df.rename(columns={"timestamp": "date"}, inplace=True)
                    df["date"] = pd.to_datetime(df["date"]).dt.date

                    for sym, g in df.groupby("symbol"):
                        hist = self._db_get_recent_bars(sym, 20) or pd.DataFrame()
                        merged = pd.concat([hist, g[["date", "open", "high", "low", "close", "volume"]]], ignore_index=True)
                        merged = merged.sort_values("date").reset_index(drop=True)
                        closes = merged["close"].astype(float)
                        highs = merged["high"].astype(float)
                        lows = merged["low"].astype(float)

                        rsi_val = self.calculate_rsi(list(closes.values)) if len(closes) >= 15 else None
                        atr_val = self.calculate_atr(list(highs.values), list(lows.values), list(closes.values)) if len(closes) >= 15 else None

                        latest_row = g.iloc[-1]
                        self._db_upsert_row({
                            "symbol": sym,
                            "date": str(latest_row["date"]),
                            "open": float(latest_row["open"]),
                            "high": float(latest_row["high"]),
                            "low": float(latest_row["low"]),
                            "close": float(latest_row["close"]),
                            "volume": int(latest_row["volume"]),
                            "adjusted_close": float(latest_row.get("close", latest_row["close"])),
                            "rsi": round(rsi_val, 2) if rsi_val is not None else None,
                            "atr": round(atr_val, 4) if atr_val is not None else None,
                        })
                        updated += 1
                except Exception as ce:
                    print(f"DB update chunk failed: {ce}", file=sys.stderr)
                    continue

            print(f"Database update completed. Upserted {updated} rows for {target_date}", file=sys.stderr)
        except Exception as e:
            print(f"Database update failed: {e}", file=sys.stderr)

    # --- Self-healing backfill ---
    def heal_database(self, start_date: str, end_date: str) -> None:
        """Audit and backfill missing rows without overwriting existing OHLC.
        - Determines trading days from QQQ bars between start_date and end_date
        - For each NASDAQ symbol, finds missing dates and inserts only those (INSERT OR IGNORE)
        - Recomputes RSI/ATR only for rows with NULL indicators
        """
        try:
            # Build trading day set from QQQ in DB, fallback to API if needed
            trading_days = set()
            qqq_df = self._db_get_recent_bars("QQQ", 2600) or pd.DataFrame()
            if not qqq_df.empty:
                mask = (qqq_df["date"] >= start_date) & (qqq_df["date"] <= end_date)
                for d in qqq_df.loc[mask, "date"].astype(str).tolist():
                    trading_days.add(d)
            if not trading_days:
                from alpaca.data.requests import StockBarsRequest
                from alpaca.data.timeframe import TimeFrame
                req = StockBarsRequest(symbol_or_symbols="QQQ", timeframe=TimeFrame.Day, start=start_date, end=end_date)
                resp = self.data_client.get_stock_bars(req)
                if resp and "QQQ" in resp.data:
                    for b in resp.data["QQQ"]:
                        trading_days.add(str(pd.to_datetime(b.timestamp).date()))
            if not trading_days:
                print("No trading days resolved for heal window", file=sys.stderr)
                return

            symbols = self.get_liquid_stocks()
            if not symbols:
                print("No symbols found for heal", file=sys.stderr)
                return

            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            from alpaca.data.enums import Adjustment

            healed = 0
            for chunk in self._chunk(symbols, 200):
                try:
                    # Fetch whole window once for the chunk
                    req = StockBarsRequest(
                        symbol_or_symbols=chunk,
                        timeframe=TimeFrame.Day,
                        start=start_date,
                        end=end_date,
                        adjustment=Adjustment.ALL,
                        limit=10000,
                    )
                    resp = self.data_client.get_stock_bars(req)
                    if not resp or not hasattr(resp, "df") or resp.df is None or resp.df.empty:
                        continue
                    df = resp.df.reset_index()
                    df.rename(columns={"timestamp": "date"}, inplace=True)
                    df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)

                    with self._db_conn() as conn:
                        for sym in chunk:
                            sdf = df[df["symbol"] == sym]
                            if sdf.empty:
                                continue
                            # Existing dates for symbol
                            existing = pd.read_sql(
                                "SELECT date FROM nasdaq_prices WHERE symbol=? AND date BETWEEN ? AND ?",
                                conn,
                                params=(sym, start_date, end_date),
                            )
                            existing_days = set(existing["date"].astype(str).tolist()) if not existing.empty else set()
                            missing_days = [d for d in sdf["date"].tolist() if d in trading_days and d not in existing_days]

                            if not missing_days:
                                # Still try to fill indicators if null on the last day
                                continue

                            for _, row in sdf[sdf["date"].isin(missing_days)].iterrows():
                                # Compute indicators using prior 20 days from DB + this row
                                hist = self._db_get_recent_bars(sym, 20) or pd.DataFrame()
                                merged = pd.concat([hist, pd.DataFrame([{
                                    "date": row["date"],
                                    "open": float(row["open"]),
                                    "high": float(row["high"]),
                                    "low": float(row["low"]),
                                    "close": float(row["close"]),
                                    "volume": int(row["volume"]),
                                }])], ignore_index=True)
                                merged = merged.sort_values("date").reset_index(drop=True)
                                closes = merged["close"].astype(float)
                                highs = merged["high"].astype(float)
                                lows = merged["low"].astype(float)
                                rsi_val = self.calculate_rsi(list(closes.values)) if len(closes) >= 15 else None
                                atr_val = self.calculate_atr(list(highs.values), list(lows.values), list(closes.values)) if len(closes) >= 15 else None

                                self._db_insert_ignore_row({
                                    "symbol": sym,
                                    "date": row["date"],
                                    "open": float(row["open"]),
                                    "high": float(row["high"]),
                                    "low": float(row["low"]),
                                    "close": float(row["close"]),
                                    "volume": int(row["volume"]),
                                    "adjusted_close": float(row.get("close", row["close"])),
                                    "rsi": round(rsi_val, 2) if rsi_val is not None else None,
                                    "atr": round(atr_val, 4) if atr_val is not None else None,
                                })
                                # Ensure indicators are set if previously null
                                self._db_update_indicators_if_null(sym, row["date"],
                                                                  round(rsi_val, 2) if rsi_val is not None else None,
                                                                  round(atr_val, 4) if atr_val is not None else None)
                                healed += 1
                except Exception as ce:
                    print(f"Heal chunk failed: {ce}", file=sys.stderr)
                    continue

            print(f"Heal complete. Inserted missing rows: {healed}", file=sys.stderr)
        except Exception as e:
            print(f"Heal failed: {e}", file=sys.stderr)
    
    def _is_preferred_exchange(self, exchange: Optional[Any]) -> bool:
        """Check if exchange is preferred (NASDAQ only)"""
        if exchange is None:
            return False
        if isinstance(exchange, AssetExchange):
            exchange = exchange.value
        return exchange == AssetExchange.NASDAQ.value
    
    def _chunk(self, seq: List[str], size: int) -> List[List[str]]:
        """Split sequence into chunks"""
        return [seq[i : i + size] for i in range(0, len(seq), size)]
    
    
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI for a series of prices"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_atr(self, high, low, close, period=14):
        """Calculate Average True Range"""
        if len(high) < period:
            return 1.0
        
        high = np.array(high)
        low = np.array(low)
        close = np.array(close)
        
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        atr = np.mean(tr[-period:])
        return atr
    
    
    
    def detect_flag_breakout_setup(self, bars: List[Bar], symbol: str) -> Optional[SetupTag]:
        """Detect flag breakout setup"""
        if len(bars) < 60:
            return None
        
        closes = [float(bar.close) for bar in bars]
        highs = [float(bar.high) for bar in bars]
        lows = [float(bar.low) for bar in bars]
        
        # Look for prior impulse (30%+ move in last 60 days)
        impulse_detected = False
        impulse_pct = 0
        
        for i in range(20, len(bars) - 20):
            window_high = max(highs[i-20:i+20])
            window_low = min(lows[i-20:i+20])
            
            if window_high > window_low:
                move_pct = (window_high - window_low) / window_low
                if move_pct >= 0.30:
                    impulse_detected = True
                    impulse_pct = move_pct * 100
                    break
        
        if not impulse_detected:
            return None
        
        # Check for tight flag consolidation (last 20 days)
        recent_closes = closes[-20:]
        recent_highs = highs[-20:]
        recent_lows = lows[-20:]
        
        # Check for higher lows
        higher_lows = 0
        for i in range(1, len(recent_lows)):
            if recent_lows[i] > recent_lows[i-1]:
                higher_lows += 1
        
        # Check for ATR contraction
        atr_values = []
        for i in range(1, len(recent_closes)):
            tr = max(
                recent_highs[i] - recent_lows[i],
                abs(recent_highs[i] - recent_closes[i-1]),
                abs(recent_lows[i] - recent_closes[i-1])
            )
            atr_values.append(tr)
        
        if len(atr_values) < 10:
            return None
        
        recent_atr = np.mean(atr_values[-10:])
        baseline_atr = np.mean(atr_values[:10])
        atr_contraction = recent_atr / baseline_atr if baseline_atr > 0 else 1.0
        
        # Check if all criteria are met
        flag_days = len(recent_closes)
        if not (impulse_pct >= 30 and atr_contraction < 1.0 and higher_lows >= 3):
            return None
        
        # Check for actual breakout above recent high
        recent_high = max(recent_highs)
        current_price = recent_closes[-1]
        breakout_above_high = current_price > recent_high * 1.015
        
        if not breakout_above_high:
            return None
        
        return SetupTag(
            setup="Flag Breakout",
            triggered=True,
            score=1.0,
            meta={
                "impulse_pct": impulse_pct,
                "flag_days": flag_days,
                "atr_contraction": atr_contraction,
                "higher_lows_count": higher_lows,
                "breakout_above_high": breakout_above_high
            }
        )
    
    def detect_range_breakout_setup(self, bars: List[Bar], symbol: str) -> Optional[SetupTag]:
        """Detect range breakout setup"""
        if len(bars) < 60:
            return None
        
        closes = np.array([float(bar.close) for bar in bars])
        highs = np.array([float(bar.high) for bar in bars])
        lows = np.array([float(bar.low) for bar in bars])
        vols = np.array([float(bar.volume) for bar in bars])
        
        # Check for tight range (last 30 days)
        base_len = 30
        base_closes = closes[-base_len:]
        range_high = float(np.max(base_closes))
        range_low = float(np.min(base_closes))
        range_size = range_high - range_low
        
        if range_low <= 0 or range_size <= 0:
            return None
        
        range_pct = range_size / range_low
        tight_base = range_pct <= 0.15  # 15% max range width
        
        if not tight_base:
            return None
        
        # Check for breakout above range
        min_break_price = range_high * 1.015  # 1.5% above range high
        price_break = closes[-1] >= min_break_price
        
        if not price_break:
            return None
        
        # Check for volume expansion
        vol_ma = np.mean(vols[-50:-1])
        vol_spike = vols[-1] >= vol_ma * 1.5
        
        if not vol_spike:
            return None
        
        # Check if all criteria are met
        breakout_strength = (closes[-1] - range_high) / range_size
        volume_mult = vols[-1] / max(vol_ma, 1e-9)
        
        if not (breakout_strength > 0 and volume_mult >= 1.5 and range_pct <= 0.15):
            return None
        
        return SetupTag(
            setup="Range Breakout",
            triggered=True,
            score=1.0,
            meta={
                "range_high": range_high,
                "range_low": range_low,
                "range_size": range_size,
                "range_pct": range_pct,
                "breakout_strength": breakout_strength,
                "volume_mult": volume_mult
            }
        )
    
    def kristjan_checklist(self, symbol: str, bars: list, benchmark_bars: list = None) -> str:
        """Kristjan-style breakout checklist with numeric stats and +/- ratings"""
        closes = np.array([float(bar.close) for bar in bars])
        highs = np.array([float(bar.high) for bar in bars])
        lows = np.array([float(bar.low) for bar in bars])
        vols = np.array([float(bar.volume) for bar in bars])

        # --- 1. Price and daily change
        price = closes[-1]
        prev_close = closes[-2]
        pct_change = (price / prev_close - 1) * 100

        # --- 2. Range tightness (last 30 bars)
        base_high = np.max(closes[-30:])
        base_low = np.min(closes[-30:])
        range_pct = (base_high - base_low) / base_low * 100
        range_ref = 15.0
        tight_flag = "+" if range_pct <= range_ref else "-"

        # --- 3. ATR contraction (14d vs 50d)
        def atr(h, l, c, n=14):
            prev = np.roll(c, 1)
            prev[0] = c[0]
            tr = np.maximum.reduce([h - l, abs(h - prev), abs(l - prev)])
            return np.mean(tr[-n:])
        
        atr14 = atr(highs, lows, closes, 14)
        atr50 = np.mean([atr(highs[i-14:i], lows[i-14:i], closes[i-14:i])
                         for i in range(14, len(closes))][-50:])
        atr_ratio = atr14 / atr50 if atr50 > 0 else np.nan
        atr_flag = "+" if atr_ratio <= 0.8 else "-"

        # --- 4. Volume expansion
        vol50 = np.mean(vols[-51:-1])
        vol_mult = vols[-1] / vol50 if vol50 > 0 else 1
        vol_flag = "+" if vol_mult >= 1.5 else "-"
        vol_now_m = vols[-1] / 1e6
        vol_ref_m = vol50 / 1e6

        # --- 5. Market filter (QQQ Current/10DMA/20DMA) - if benchmark provided
        market_flag = "+"
        market_ref = "10>20+"
        bench_current = 0.0
        bench_10 = 0.0
        bench_20 = 0.0
        if benchmark_bars and len(benchmark_bars) >= 21:  # Need 21 for 10DMA trend
            bench_close = np.array([float(b.close) for b in benchmark_bars])
            bench_current = bench_close[-1]  # Current QQQ price
            bench_10 = np.mean(bench_close[-10:])
            bench_20 = np.mean(bench_close[-20:])
            # Check 10DMA is above 20DMA AND trending higher
            bench_10_prev = np.mean(bench_close[-11:-1])  # Previous 10DMA
            market_condition = (bench_10 > bench_20) and (bench_10 > bench_10_prev)
            market_flag = "+" if market_condition else "-"
        else:
            market_flag = "?"  # Unknown if no benchmark data

        # --- 6. Breakout distance from base high
        breakout_pct = (price / base_high - 1) * 100
        breakout_ref = 1.5
        breakout_flag = "+" if breakout_pct >= breakout_ref else "-"

        # --- 7. Compose output
        checklist = (
            f"${symbol} {price:.2f} {pct_change:+.1f}% | "
            f"Range {range_pct:.1f}/{range_ref:.0f}%{tight_flag} | "
            f"ATR {atr14:.2f}/{atr50:.2f} ({atr_ratio:.2f}×){atr_flag} | "
            f"V {vol_now_m:.1f}M/{vol_ref_m:.1f}M ({vol_mult:.1f}×){vol_flag} | "
            f"B {breakout_pct:.1f}/{breakout_ref:.1f}%{breakout_flag}"
        )
        
        return checklist
    
    def get_qqq_market_signal(self, benchmark_bars: list = None) -> str:
        """Get daily QQQ market signal at market open"""
        if not benchmark_bars or len(benchmark_bars) < 21:
            return "$QQQ N/A/N/A/N/A ?"
        
        bench_close = np.array([float(b.close) for b in benchmark_bars])
        bench_current = bench_close[-1]
        bench_10 = np.mean(bench_close[-10:])
        bench_20 = np.mean(bench_close[-20:])
        
        # Check 10DMA is above 20DMA AND trending higher
        bench_10_prev = np.mean(bench_close[-11:-1])
        market_condition = (bench_10 > bench_20) and (bench_10 > bench_10_prev)
        market_flag = "+" if market_condition else "-"
        
        return f"$QQQ {bench_current:,.0f}/{bench_10:,.0f}/{bench_20:,.0f} {market_flag}"
    
    def send_email_notification(self, signals: List[str]):
        """Send email notification with signals"""
        if not signals:
            return
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = "analyst@asymmetric.com"
            msg['To'] = self.config.EMAIL_RECIPIENT
            msg['Subject'] = self.config.EMAIL_SUBJECT
            
            # Create body
            body = "Breakout Signals Detected:\n\n"
            for signal in signals:
                body += f"{signal}\n"
            
            body += f"\nGenerated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}"
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email (this would need proper SMTP configuration)
            print(f"Email notification prepared for {len(signals)} signals", file=sys.stderr)
            print(f"Recipient: {self.config.EMAIL_RECIPIENT}", file=sys.stderr)
            
            # For now, just print the email content
            print("\n" + "="*50)
            print("EMAIL NOTIFICATION:")
            print("="*50)
            print(body)
            print("="*50)
            
        except Exception as e:
            print(f"Email notification failed: {e}", file=sys.stderr)
    
    def scan_breakouts(self, max_stocks: int = None, benchmark_bars: list = None) -> List[Dict]:
        """Scan for breakout signals"""
        print("Scanning for breakout signals...", file=sys.stderr)
        
        # Get liquid stocks
        symbols = self.get_liquid_stocks()
        if max_stocks:
            symbols = symbols[:max_stocks]
        
        print(f"Analyzing {len(symbols)} stocks...", file=sys.stderr)
        
        setups = []
        
        for i, symbol in enumerate(symbols):
            try:
                print(f"Analyzing {symbol} ({i+1}/{len(symbols)})...", file=sys.stderr)
                
                # Prefer reading last 90 days from local DB; fallback to API
                df = self._db_get_recent_bars(symbol, 90)
                symbol_bars = []
                if df is not None and not df.empty:
                    class SimpleBar:
                        def __init__(self, r):
                            self.close = r["close"]
                            self.high = r["high"]
                            self.low = r["low"]
                            self.volume = r["volume"]
                    symbol_bars = [SimpleBar(r) for _, r in df.iterrows()]
                else:
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=90)
                    request = StockBarsRequest(
                        symbol_or_symbols=symbol,
                        timeframe=TimeFrame.Day,
                        start=start_date,
                        end=end_date
                    )
                    bars = self.data_client.get_stock_bars(request)
                    if not bars or symbol not in bars.data:
                        continue
                    symbol_bars = bars.data[symbol]
                if len(symbol_bars) < 30:
                    continue
                
                # Calculate technical indicators
                closes = [float(bar.close) for bar in symbol_bars]
                highs = [float(bar.high) for bar in symbol_bars]
                lows = [float(bar.low) for bar in symbol_bars]
                
                rsi = self.calculate_rsi(closes)
                atr = self.calculate_atr(highs, lows, closes)
                
                # Calculate change percentage
                if len(closes) >= 2:
                    change_pct = ((closes[-1] - closes[-2]) / closes[-2]) * 100
                else:
                    change_pct = 0.0
                
                # Detect breakouts
                flag_breakout = self.detect_flag_breakout_setup(symbol_bars, symbol)
                range_breakout = self.detect_range_breakout_setup(symbol_bars, symbol)
                
                # Add flag breakout if found
                if flag_breakout:
                    setups.append({
                        'symbol': symbol,
                        'setup': flag_breakout,
                        'price': float(symbol_bars[-1].close),
                        'change_pct': change_pct,
                        'rsi': rsi,
                        'tr_atr': atr,
                        'bars': symbol_bars
                    })
                
                # Add range breakout if found
                if range_breakout:
                    setups.append({
                        'symbol': symbol,
                        'setup': range_breakout,
                        'price': float(symbol_bars[-1].close),
                        'change_pct': change_pct,
                        'rsi': rsi,
                        'tr_atr': atr,
                        'bars': symbol_bars
                    })
                
            except Exception as e:
                print(f"Error processing {symbol}: {e}", file=sys.stderr)
                continue
        
        # Sort by setup score
        def sort_key(x):
            base_score = x['setup'].score
            if x['setup'].setup == "Flag Breakout":
                return base_score + 0.1
            return base_score
        
        setups.sort(key=sort_key, reverse=True)
        
        print(f"Found {len(setups)} breakout signals", file=sys.stderr)
        
        return setups
    
    def execute_trade(self, signal: Dict) -> bool:
        """Execute a trade based on signal"""
        try:
            symbol = signal['symbol']
            price = signal['price']
            
            # Get account info
            account = self.trading_client.get_account()
            buying_power = float(account.buying_power)
            
            if buying_power < 1000:
                print(f"Insufficient buying power: ${buying_power:,.2f}", file=sys.stderr)
                return False
            
            # Calculate position size
            position_value = buying_power * self.config.MAX_POSITION_SIZE
            quantity = int(position_value / price)
            
            if quantity < 1:
                print(f"Position size too small for {symbol}: {quantity} shares", file=sys.stderr)
                return False
            
            # Place market order
            from alpaca.trading.requests import MarketOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce
            
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            
            order = self.trading_client.submit_order(order_request)
            
            # Update portfolio state
            self.portfolio["positions"][symbol] = {
                "shares": quantity,
                "entry_price": price,
                "entry_time": datetime.now().isoformat(),
                "stop_loss": price * (1 - self.config.STOP_LOSS_PCT),
                "take_profit": price * (1 + self.config.TAKE_PROFIT_PCT)
            }
            
            self.save_portfolio_state()
            
            print(f"BUY ORDER: {quantity} shares of {symbol} at ${price:.2f}", file=sys.stderr)
            return True
            
        except Exception as e:
            print(f"Trade execution failed for {symbol}: {e}", file=sys.stderr)
            return False
    
    def get_benchmark_data(self):
        """Get QQQ benchmark data for market filter"""
        try:
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)  # Only need 30 days for 20DMA
            
            benchmark_request = StockBarsRequest(
                symbol_or_symbols="QQQ",
                timeframe=TimeFrame.Day,
                start=start_date,
                end=end_date
            )
            
            benchmark_data = self.data_client.get_stock_bars(benchmark_request)
            if benchmark_data and "QQQ" in benchmark_data.data:
                benchmark_bars = benchmark_data.data["QQQ"]
                print(f"Loaded {len(benchmark_bars)} QQQ bars for benchmark", file=sys.stderr)
                return benchmark_bars
            else:
                print("Warning: Could not load QQQ benchmark data", file=sys.stderr)
                return None
                
        except Exception as e:
            print(f"Warning: Could not load benchmark data: {e}", file=sys.stderr)
            return None

    def run_analysis(self, max_stocks: int = None, top_n: int = 10):
        """Run the complete analysis"""
        print("Unified Analyst - Breakout Detection", file=sys.stderr)
        print("=" * 50, file=sys.stderr)
        
        # Check market hours
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute
        current_dow = datetime.now().weekday()  # 0=Monday, 6=Sunday
        
        # Get benchmark data for market filter (prefer DB)
        benchmark_bars = None
        try:
            qqq_df = self._db_get_benchmark_bars("QQQ", 30)
            if qqq_df is not None and not qqq_df.empty:
                class SimpleBar:
                    def __init__(self, r):
                        self.close = r["close"]
                        self.high = r["high"]
                        self.low = r["low"]
                        self.volume = r["volume"]
                benchmark_bars = [SimpleBar(r) for _, r in qqq_df.iterrows()]
        except Exception:
            pass
        if benchmark_bars is None:
            benchmark_bars = self.get_benchmark_data()
        
        # Send QQQ signal at 9:30 AM (market open)
        if (current_hour == 9 and current_minute == 30 and current_dow < 5):
            print("Market Open - Sending QQQ Signal", file=sys.stderr)
            if benchmark_bars:
                qqq_signal = self.get_qqq_market_signal(benchmark_bars)
                print(qqq_signal)
            return
        
        # Regular stock scanning (after 9:30 AM)
        if (self.config.SCHEDULE_START <= current_hour < self.config.SCHEDULE_END and 
            current_dow < 5):  # Weekdays
            print("Market is open - scanning individual stocks", file=sys.stderr)
        else:
            print("Market is closed - running analysis anyway", file=sys.stderr)
        
        # Scan for breakouts
        signals = self.scan_breakouts(max_stocks, benchmark_bars)
        
        if not signals:
            print("No breakout signals found", file=sys.stderr)
            return
        
        # Show top signals
        top_signals = signals[:top_n]
        
        # Format and output signals using long format
        formatted_signals = []
        for signal in top_signals:
            symbol = signal['symbol']
            bars = signal['bars']
            
            # Use kristjan checklist format with benchmark data
            signal_str = self.kristjan_checklist(symbol, bars, benchmark_bars)
            print(signal_str)
            formatted_signals.append(signal_str)
        
        # Send email notifications
        if formatted_signals:
            self.send_email_notification(formatted_signals)
        
        # Execute trades if auto-trade is enabled
        if self.auto_trade and signals:
            print("\nAuto-trading enabled...", file=sys.stderr)
            
            # Only trade the top signal if it meets criteria
            top_signal = signals[0]
            if (top_signal['setup'].score >= 0.7 and 
                top_signal['rsi'] >= 40 and top_signal['rsi'] <= 70):
                
                success = self.execute_trade(top_signal)
                if success:
                    print(f"Trade executed for {top_signal['symbol']}", file=sys.stderr)
                else:
                    print(f"Trade failed for {top_signal['symbol']}", file=sys.stderr)
            else:
                print("No high-confidence signals for trading", file=sys.stderr)

def main():
    """Main function with command-line interface"""
    parser = argparse.ArgumentParser(description='Unified Analyst - Breakout Detection System')
    parser.add_argument('--mode', choices=['breakout', 'advanced', 'mcp'], default='breakout',
                       help='Analysis mode (default: breakout)')
    parser.add_argument('--scan', action='store_true',
                       help='Run single scan (default: daemon mode)')
    parser.add_argument('--daemon', action='store_true',
                       help='Run in daemon mode (continuous monitoring)')
    parser.add_argument('--auto-trade', action='store_true',
                       help='Enable automatic trading')
    parser.add_argument('--use-mcp', action='store_true',
                       help='Use MCP integration')
    parser.add_argument('--max-stocks', type=int, default=30,
                       help='Maximum number of stocks to analyze')
    parser.add_argument('--top-n', type=int, default=10,
                       help='Number of top signals to show')
    
    args = parser.parse_args()
    
    # Create analyst instance
    analyst = UnifiedAnalyst(
        mode=args.mode,
        use_mcp=args.use_mcp,
        auto_trade=args.auto_trade
    )
    
    try:
        if args.scan:
            # Single scan mode
            analyst.run_analysis(max_stocks=args.max_stocks, top_n=args.top_n)
        elif args.daemon:
            # Daemon mode (continuous monitoring)
            print("Starting daemon mode...", file=sys.stderr)
            print("Monitoring every 30 minutes during market hours", file=sys.stderr)
            print("Press Ctrl+C to stop", file=sys.stderr)
            
            import time
            while True:
                try:
                    analyst.run_analysis(max_stocks=args.max_stocks, top_n=args.top_n)
                    print("Waiting 30 minutes...", file=sys.stderr)
                    time.sleep(1800)  # 30 minutes
                except KeyboardInterrupt:
                    print("\nDaemon stopped by user", file=sys.stderr)
                    break
                except Exception as e:
                    print(f"Daemon error: {e}", file=sys.stderr)
                    time.sleep(300)  # Wait 5 minutes before retry
        else:
            # Default: single scan
            analyst.run_analysis(max_stocks=args.max_stocks, top_n=args.top_n)
    
    except Exception as e:
        print(f"Analysis failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
