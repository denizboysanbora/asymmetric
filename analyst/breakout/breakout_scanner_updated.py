#!/usr/bin/env python3
"""
Updated Breakout Scanner with Unified Parameters
- 20-day base for both Flag and Range breakouts
- 25% tight base threshold for both
- Higher lows required for Range, optional for Flag
- Market filter added to Flag breakout
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from pydantic import BaseModel, Field

# Load environment variables first
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent / "config" / "api_keys.env"
    if env_file.exists():
        load_dotenv(env_file)
        print("🔑 Loaded API keys from .env file", file=sys.stderr)
except ImportError:
    pass

# Add alpaca directory to path
ALPACA_DIR = Path(__file__).parent.parent / "input" / "alpaca"
sys.path.insert(0, str(ALPACA_DIR))

# Import Alpaca modules
try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
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

def _sma(arr: np.ndarray, n: int) -> np.ndarray:
    """Simple Moving Average"""
    if len(arr) < n:
        return np.full_like(arr, fill_value=np.nan, dtype=float)
    w = np.ones(n) / n
    out = np.convolve(arr, w, mode='full')[:len(arr)]
    out[:n-1] = np.nan
    return out

def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    """Average True Range calculation"""
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr = np.maximum.reduce([
        high - low,
        np.abs(high - prev_close),
        np.abs(low - prev_close)
    ])
    atr = _sma(tr, n)
    return atr

def _higher_lows_pivots(lows: np.ndarray, left: int = 3, right: int = 3, needed: int = 3) -> bool:
    """Simple pivot-low detector: a pivot at i if low[i] is the min in [i-left, i+right].
    Returns True if the last `needed` pivots are strictly increasing.
    """
    n = len(lows)
    pivots = []
    for i in range(left, n - right):
        window = lows[i-left:i+right+1]
        if np.argmin(window) == left:
            pivots.append((i, lows[i]))
    if len(pivots) < needed:
        return False
    last = [p[1] for p in pivots[-needed:]]
    return last[0] < last[1] < last[2]

def detect_flag_breakout_setup(
    bars: List[Bar], 
    symbol: str, 
    benchmark_closes: Optional[List[float]] = None,
    base_len: int = 20,  # UPDATED: 20-day base
    max_range_width_pct: float = 25.0,  # UPDATED: 25% tight base
    atr_len: int = 14,
    atr_ma: int = 50,
    atr_ratio_thresh: float = 1.2,  # UPDATED: Relaxed to 1.2
    require_higher_lows: bool = False,  # Keep optional for Flag
    min_break_above_pct: float = 1.0,  # Keep relaxed threshold
    vol_ma: int = 50,
    vol_mult: float = 1.5,
    use_market_filter: bool = True  # UPDATED: Add market filter to Flag
) -> Optional[SetupTag]:
    """
    Updated Flag Breakout detector with unified parameters.
    Uses 20-day base, 25% tight base threshold, and includes market filter.
    """
    min_needed = max(base_len + 1, atr_ma + atr_len + 1, vol_ma + 1, 60)
    if len(bars) < min_needed:
        return None

    closes = np.array([float(b.close) for b in bars], dtype=float)
    highs  = np.array([float(b.high)  for b in bars], dtype=float)
    lows   = np.array([float(b.low)   for b in bars], dtype=float)
    vols   = np.array([float(b.volume) for b in bars], dtype=float)

    # Look for prior impulse (30%+ move in last 60 days)
    impulse_detected = False
    impulse_pct = 0
    
    for i in range(20, len(bars) - 20):
        window_high = max(highs[i-20:i+20])
        window_low = min(lows[i-20:i+20])
        
        if window_high > window_low:
            move_pct = (window_high - window_low) / window_low
            if move_pct >= 0.30:  # 30%+ move
                impulse_detected = True
                impulse_pct = move_pct * 100
                break
    
    if not impulse_detected:
        return None

    # --- Tight Base Analysis (20-day) ---
    base_slice = slice(-base_len, None)
    base_closes = closes[base_slice]
    range_high = float(np.max(base_closes))
    range_low  = float(np.min(base_closes))
    range_size = range_high - range_low
    if range_low <= 0 or range_size <= 0:
        return None
    range_pct = range_size / range_low
    tight_base = range_pct <= (max_range_width_pct / 100.0)

    # --- ATR contraction ---
    atr_series = _atr(highs, lows, closes, atr_len)
    atr_ma_series = _sma(atr_series, atr_ma)
    atr_ratio = float(atr_series[-1] / atr_ma_series[-1]) if (not np.isnan(atr_series[-1]) and not np.isnan(atr_ma_series[-1]) and atr_ma_series[-1] != 0) else np.nan
    contraction_ok = (not np.isnan(atr_ratio)) and (atr_ratio <= atr_ratio_thresh)

    # --- Higher lows structure (optional for Flag) ---
    structure_ok = True
    if require_higher_lows:
        structure_ok = _higher_lows_pivots(lows[-base_len:])

    # --- Breakout confirmation (price + volume) ---
    min_break_price = range_high * (1.0 + min_break_above_pct / 100.0)
    price_break = closes[-1] >= min_break_price

    vol_ma_series = _sma(vols, vol_ma)
    vol_spike = (not np.isnan(vol_ma_series[-1])) and (vol_ma_series[-1] > 0) and (vols[-1] >= vol_mult * vol_ma_series[-1])

    breakout_ok = price_break and vol_spike

    # --- Market filter (NEW for Flag) ---
    rs_ok = True
    market_ok = True
    bench_info: Dict[str, Any] = {}

    if benchmark_closes is not None and len(benchmark_closes) == len(closes):
        bench = np.array(benchmark_closes, dtype=float)
        # RS: price / benchmark > SMA50(RS)
        with np.errstate(divide='ignore', invalid='ignore'):
            rs = closes / bench
        rs_ma50 = _sma(rs, 50)
        rs_ok = (not np.isnan(rs[-1])) and (not np.isnan(rs_ma50[-1])) and (rs[-1] > rs_ma50[-1])

        # Market filter: 10DMA > 20DMA and 10DMA rising
        sma10 = _sma(bench, 10)
        sma20 = _sma(bench, 20)
        sma10_up = (not np.isnan(sma10[-1])) and (not np.isnan(sma10[-2])) and (sma10[-1] > sma10[-2])
        market_ok = (sma10[-1] > sma20[-1]) and sma10_up if use_market_filter else True

        bench_info = {
            "benchmark_10dma": float(sma10[-1]) if not np.isnan(sma10[-1]) else None,
            "benchmark_20dma": float(sma20[-1]) if not np.isnan(sma20[-1]) else None,
            "benchmark_10dma_up": bool(sma10_up) if not np.isnan(sma10[-1]) and not np.isnan(sma10[-2]) else None,
            "rs": float(rs[-1]) if not np.isnan(rs[-1]) else None,
            "rs_sma50": float(rs_ma50[-1]) if not np.isnan(rs_ma50[-1]) else None
        }

    # --- Final decision ---
    all_ok = tight_base and contraction_ok and structure_ok and breakout_ok and rs_ok and market_ok

    # Only return if ALL criteria are met
    if not all_ok:
        return None

    # --- Scoring ---
    breakout_strength = (closes[-1] - range_high) / range_size if range_size > 0 else 0
    volume_mult_eff = vols[-1] / max(vol_ma_series[-1], 1e-9) if not np.isnan(vol_ma_series[-1]) else 1.0
    volume_score = min(volume_mult_eff / (vol_mult * 2.0), 1.0)
    range_quality = max(0.0, 1.0 - (range_pct / (max_range_width_pct / 100.0)))
    atr_score = min(atr_ratio_thresh / max(atr_ratio, 1e-9), 1.0) if not np.isnan(atr_ratio) else 0.0
    rs_mkt_bonus = 1.0 if (rs_ok and market_ok) else 0.0

    score = (
        0.30 * max(0.0, min(breakout_strength, 1.0)) +
        0.25 * volume_score +
        0.25 * range_quality +
        0.15 * atr_score +
        0.05 * rs_mkt_bonus
    )

    return SetupTag(
        setup="Flag Breakout",
        triggered=True,
        score=float(max(0.0, min(score, 1.0))),
        meta={
            "symbol": symbol,
            "entry": float(closes[-1]),
            "stop": float(range_low),
            "base_len": base_len,
            "range_high": range_high,
            "range_low": range_low,
            "range_size": range_size,
            "range_pct": range_pct,
            "tight_base": tight_base,
            "min_break_price": float(min_break_price),
            "price_break": bool(price_break),
            "volume": float(vols[-1]),
            "vol_ma": float(vol_ma_series[-1]) if not np.isnan(vol_ma_series[-1]) else None,
            "volume_mult": float(volume_mult_eff) if not np.isnan(vol_ma_series[-1]) else None,
            "vol_spike": bool(vol_spike),
            "atr_ratio": float(atr_ratio) if not np.isnan(atr_ratio) else None,
            "contraction_ok": bool(contraction_ok),
            "higher_lows": bool(structure_ok),
            "rs_ok": bool(rs_ok),
            "market_ok": bool(market_ok),
            "impulse_pct": impulse_pct,
            **bench_info
        }
    )

def detect_range_breakout_setup(
    bars: List[Bar], 
    symbol: str, 
    benchmark_closes: Optional[List[float]] = None,
    base_len: int = 20,  # UPDATED: 20-day base
    max_range_width_pct: float = 25.0,  # UPDATED: 25% tight base
    atr_len: int = 14,
    atr_ma: int = 50,
    atr_ratio_thresh: float = 1.2,  # UPDATED: Relaxed to 1.2
    require_higher_lows: bool = True,  # Keep required for Range
    min_break_above_pct: float = 1.5,
    vol_ma: int = 50,
    vol_mult: float = 1.5,
    use_market_filter: bool = True
) -> Optional[SetupTag]:
    """
    Updated Range Breakout detector with unified parameters.
    Uses 20-day base, 25% tight base threshold, keeps higher lows required.
    """
    min_needed = max(base_len + 1, atr_ma + atr_len + 1, vol_ma + 1, 60)
    if len(bars) < min_needed:
        return None

    closes = np.array([float(b.close) for b in bars], dtype=float)
    highs  = np.array([float(b.high)  for b in bars], dtype=float)
    lows   = np.array([float(b.low)   for b in bars], dtype=float)
    vols   = np.array([float(b.volume) for b in bars], dtype=float)

    # --- Base (range) using last base_len bars (close-based) ---
    base_slice = slice(-base_len, None)
    base_closes = closes[base_slice]
    range_high = float(np.max(base_closes))
    range_low  = float(np.min(base_closes))
    range_size = range_high - range_low
    if range_low <= 0 or range_size <= 0:
        return None
    range_pct = range_size / range_low
    tight_base = range_pct <= (max_range_width_pct / 100.0)

    # --- ATR contraction (full series; evaluate last bar) ---
    atr_series = _atr(highs, lows, closes, atr_len)
    atr_ma_series = _sma(atr_series, atr_ma)
    atr_ratio = float(atr_series[-1] / atr_ma_series[-1]) if (not np.isnan(atr_series[-1]) and not np.isnan(atr_ma_series[-1]) and atr_ma_series[-1] != 0) else np.nan
    contraction_ok = (not np.isnan(atr_ratio)) and (atr_ratio <= atr_ratio_thresh)

    # --- Higher lows structure (required for Range) ---
    structure_ok = True
    if require_higher_lows:
        structure_ok = _higher_lows_pivots(lows[-base_len:])

    # --- Breakout confirmation (price + volume) ---
    min_break_price = range_high * (1.0 + min_break_above_pct / 100.0)
    price_break = closes[-1] >= min_break_price

    vol_ma_series = _sma(vols, vol_ma)
    vol_spike = (not np.isnan(vol_ma_series[-1])) and (vol_ma_series[-1] > 0) and (vols[-1] >= vol_mult * vol_ma_series[-1])

    breakout_ok = price_break and vol_spike

    # --- Relative strength & market filter ---
    rs_ok = True
    market_ok = True
    bench_info: Dict[str, Any] = {}

    if benchmark_closes is not None and len(benchmark_closes) == len(closes):
        bench = np.array(benchmark_closes, dtype=float)
        # RS: price / benchmark > SMA50(RS)
        with np.errstate(divide='ignore', invalid='ignore'):
            rs = closes / bench
        rs_ma50 = _sma(rs, 50)
        rs_ok = (not np.isnan(rs[-1])) and (not np.isnan(rs_ma50[-1])) and (rs[-1] > rs_ma50[-1])

        # Market filter: 10DMA > 20DMA and 10DMA rising
        sma10 = _sma(bench, 10)
        sma20 = _sma(bench, 20)
        sma10_up = (not np.isnan(sma10[-1])) and (not np.isnan(sma10[-2])) and (sma10[-1] > sma10[-2])
        market_ok = (sma10[-1] > sma20[-1]) and sma10_up if use_market_filter else True

        bench_info = {
            "benchmark_10dma": float(sma10[-1]) if not np.isnan(sma10[-1]) else None,
            "benchmark_20dma": float(sma20[-1]) if not np.isnan(sma20[-1]) else None,
            "benchmark_10dma_up": bool(sma10_up) if not np.isnan(sma10[-1]) and not np.isnan(sma10[-2]) else None,
            "rs": float(rs[-1]) if not np.isnan(rs[-1]) else None,
            "rs_sma50": float(rs_ma50[-1]) if not np.isnan(rs_ma50[-1]) else None
        }

    # --- Final decision ---
    range_detected = tight_base
    all_ok = range_detected and contraction_ok and structure_ok and breakout_ok and rs_ok and market_ok

    # Only return if ALL criteria are met (strict breakout confirmation)
    if not all_ok:
        return None

    # --- Scoring (0..1) to rank setups ---
    breakout_strength = (closes[-1] - range_high) / range_size  # how far into space
    volume_mult_eff = vols[-1] / max(vol_ma_series[-1], 1e-9) if not np.isnan(vol_ma_series[-1]) else 1.0
    volume_score = min(volume_mult_eff / (vol_mult * 2.0), 1.0)  # cap at 2x required multiple
    range_quality = max(0.0, 1.0 - (range_pct / (max_range_width_pct / 100.0)))  # 1 when very tight
    atr_score = min(atr_ratio_thresh / max(atr_ratio, 1e-9), 1.0) if not np.isnan(atr_ratio) else 0.0
    rs_mkt_bonus = 1.0 if (rs_ok and market_ok) else 0.0

    score = (
        0.30 * max(0.0, min(breakout_strength, 1.0)) +
        0.25 * volume_score +
        0.25 * range_quality +
        0.15 * atr_score +
        0.05 * rs_mkt_bonus
    )

    # --- Return tag ---
    entry = float(closes[-1])
    stop = float(range_low)

    return SetupTag(
        setup="Range Breakout",
        triggered=True,
        score=float(max(0.0, min(score, 1.0))),
        meta={
            "symbol": symbol,
            "entry": entry,
            "stop": stop,
            "base_len": base_len,
            "range_high": range_high,
            "range_low": range_low,
            "range_size": range_size,
            "range_pct": range_pct,
            "tight_base": tight_base,
            "min_break_price": float(min_break_price),
            "price_break": bool(price_break),
            "volume": float(vols[-1]),
            "vol_ma": float(vol_ma_series[-1]) if not np.isnan(vol_ma_series[-1]) else None,
            "volume_mult": float(volume_mult_eff) if not np.isnan(vol_ma_series[-1]) else None,
            "vol_spike": bool(vol_spike),
            "atr_ratio": float(atr_ratio) if not np.isnan(atr_ratio) else None,
            "contraction_ok": bool(contraction_ok),
            "higher_lows": bool(structure_ok),
            "rs_ok": bool(rs_ok),
            "market_ok": bool(market_ok),
            **bench_info
        }
    )
