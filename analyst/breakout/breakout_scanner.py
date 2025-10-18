#!/usr/bin/env python3
"""
Unified Breakout Scanner - Detects both flag and range breakout patterns
Output format: $SYMBOL $PRICE +X.XX% | ## RSI | X.XXx ATR | Z X.XX | Flag/Range Breakout
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
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

try:
    # Add parent directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from breakout_analysis import get_liquid_stocks
except Exception as import_exc:
    print(f"Error importing shared get_liquid_stocks: {import_exc}", file=sys.stderr)
    sys.exit(1)

class SetupTag(BaseModel):
    """Setup tag model."""
    setup: str = Field(..., description="Setup type")
    triggered: bool = Field(..., description="Whether setup is triggered")
    score: float = Field(..., description="Setup strength score (0-1)")
    meta: Dict = Field(default_factory=dict, description="Setup-specific metadata")
    
    model_config = {"extra": "allow"}

def calculate_adr_pct(prices: List[float], period: int = 20) -> float:
    """Calculate Average Daily Range percentage"""
    if len(prices) < period:
        return 0.0
    
    recent_prices = prices[-period:]
    ranges = []
    for i in range(1, len(recent_prices)):
        daily_range = abs(recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
        ranges.append(daily_range)
    
    return np.mean(ranges) * 100 if ranges else 0.0

def calculate_rs_score(prices: List[float], spy_prices: List[float]) -> float:
    """Calculate Relative Strength score"""
    if len(prices) < 20 or len(spy_prices) < 20:
        return 0.5  # Neutral if not enough data
    
    # Calculate returns
    stock_returns = np.diff(prices) / prices[:-1]
    spy_returns = np.diff(spy_prices) / spy_prices[:-1]
    
    # Calculate relative performance
    relative_performance = stock_returns - spy_returns
    rs_score = np.mean(relative_performance)
    
    # Normalize to 0-1 scale
    return max(0.0, min(1.0, (rs_score + 0.1) / 0.2))

def calculate_rsi(prices, period=14):
    """Calculate RSI for a series of prices"""
    if len(prices) < period + 1:
        return 50.0  # Default RSI if not enough data
    
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

def calculate_atr(high, low, close, period=14):
    """Calculate Average True Range"""
    if len(high) < period:
        return 1.0  # Default ATR if not enough data
    
    high = np.array(high)
    low = np.array(low)
    close = np.array(close)
    
    tr1 = high[1:] - low[1:]
    tr2 = np.abs(high[1:] - close[:-1])
    tr3 = np.abs(low[1:] - close[:-1])
    
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    atr = np.mean(tr[-period:])
    return atr

def calculate_z_score(prices, period=20):
    """Calculate Z-score for price changes"""
    if len(prices) < period + 1:
        return 0.0  # Default Z-score if not enough data
    
    changes = np.diff(prices) / prices[:-1] * 100  # Percentage changes
    if len(changes) < period:
        return 0.0
    
    recent_changes = changes[-period:]
    mean_change = np.mean(recent_changes)
    std_change = np.std(recent_changes)
    
    if std_change == 0:
        return 0.0
    
    current_change = changes[-1]
    z_score = (current_change - mean_change) / std_change
    return z_score

def detect_flag_breakout_setup(bars: List[Bar], symbol: str) -> Optional[SetupTag]:
    """Detect flag breakout setup"""
    if len(bars) < 60:  # Need at least 3 months of data
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
            if move_pct >= 0.30:  # 30%+ move
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
    
    # Calculate setup score
    flag_days = len(recent_closes)
    score = min(impulse_pct / 100, 1.0) * 0.4 + (1 - atr_contraction) * 0.3 + (higher_lows / flag_days) * 0.3
    
    # Strict criteria: Must have strong impulse, good contraction, and higher lows
    if score < 0.5:  # Higher threshold for quality
        return None
    
    # Additional check: Must have actual breakout above recent high
    recent_high = max(recent_highs)
    current_price = recent_closes[-1]
    breakout_above_high = current_price > recent_high * 1.015  # 1.5% above recent high
    
    if not breakout_above_high:
        return None
    
    return SetupTag(
        setup="Flag Breakout",
        triggered=True,  # Only triggered if actual breakout
        score=score,
        meta={
            "impulse_pct": impulse_pct,
            "flag_days": flag_days,
            "atr_contraction": atr_contraction,
            "higher_lows_count": higher_lows,
            "breakout_above_high": breakout_above_high
        }
    )

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

def detect_range_breakout_setup(
    bars: List[Bar], 
    symbol: str, 
    benchmark_closes: Optional[List[float]] = None,
    base_len: int = 30,
    max_range_width_pct: float = 15.0,
    atr_len: int = 14,
    atr_ma: int = 50,
    atr_ratio_thresh: float = 0.80,
    require_higher_lows: bool = True,
    min_break_above_pct: float = 1.5,
    vol_ma: int = 50,
    vol_mult: float = 1.5,
    use_market_filter: bool = True
) -> Optional[SetupTag]:
    """
    Enhanced Range Breakout detector.
    Adds:
      - Base (tight range) + ATR contraction
      - Optional higher-lows structure
      - Breakout: close > base_high by Y% AND volume >= V * volMA
      - Relative strength: price/benchmark > SMA(50) of RS
      - Market filter: benchmark 10DMA > 20DMA and 10DMA rising
    Returns a SetupTag or None.
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

    # --- Higher lows structure (inside base window) ---
    structure_ok = True
    if require_higher_lows:
        structure_ok = _higher_lows_pivots(lows[-base_len:])

    # --- Breakout confirmation (price + volume) ---
    min_break_price = range_high * (1.0 + min_break_above_pct / 100.0)
    price_break = closes[-1] >= min_break_price

    vol_ma_series = _sma(vols, vol_ma)
    vol_spike = (not np.isnan(vol_ma_series[-1])) and (vol_ma_series[-1] > 0) and (vols[-1] >= vol_mult * vol_ma_series[-1])

    breakout_ok = price_break and vol_spike

    # --- Relative strength & market filter (optional if benchmark provided) ---
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
    # components: (tighter base better), (how far above break), (volume multiple), (ATR contraction depth), (RS & market bonus)
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

    # --- Return tag (compatible with your existing shape) ---
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

def scan_breakout_setups(top_n=10):
    """Scan for both flag and range breakout setups"""
    try:
        # Initialize Alpaca client
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        if not api_key or not secret_key:
            print("Warning: ALPACA_API_KEY and ALPACA_SECRET_KEY not set, no signals will be generated", file=sys.stderr)
            return []  # Return empty list - no mock data
        
        client = StockHistoricalDataClient(api_key, secret_key)
        
        # Get liquid stocks
        symbols = get_liquid_stocks()
        
        setups = []
        
        for symbol in symbols:
            try:
                # Get daily bars for last 3 months
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)
                
                request = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=TimeFrame.Day,
                    start=start_date,
                    end=end_date
                )
                
                bars = client.get_stock_bars(request)
                
                if not bars or symbol not in bars.data:
                    continue
                
                symbol_bars = bars.data[symbol]
                if len(symbol_bars) < 30:
                    continue
                
                # Calculate technical indicators once
                closes = [float(bar.close) for bar in symbol_bars]
                highs = [float(bar.high) for bar in symbol_bars]
                lows = [float(bar.low) for bar in symbol_bars]
                
                rsi = calculate_rsi(closes)
                atr = calculate_atr(highs, lows, closes)
                z_score = calculate_z_score(closes)
                adr_pct = calculate_adr_pct(closes)
                
                # Calculate change percentage
                if len(closes) >= 2:
                    change_pct = ((closes[-1] - closes[-2]) / closes[-2]) * 100
                else:
                    change_pct = 0.0
                
                # Detect both flag and range breakouts
                flag_breakout = detect_flag_breakout_setup(symbol_bars, symbol)
                range_breakout = detect_range_breakout_setup(symbol_bars, symbol)
                
                # Add flag breakout if found
                if flag_breakout:
                    setups.append({
                        'symbol': symbol,
                        'setup': flag_breakout,
                        'price': float(symbol_bars[-1].close),
                        'change_pct': change_pct,
                        'adr_pct': adr_pct,
                        'rs_score': 0.5,  # Simplified for now
                        'rsi': rsi,
                        'tr_atr': atr,
                        'z_score': z_score,
                        'bars': symbol_bars  # Store bars for Kristjan checklist
                    })
                
                # Add range breakout if found
                if range_breakout:
                    setups.append({
                        'symbol': symbol,
                        'setup': range_breakout,
                        'price': float(symbol_bars[-1].close),
                        'change_pct': change_pct,
                        'adr_pct': adr_pct,
                        'rs_score': 0.5,  # Simplified for now
                        'rsi': rsi,
                        'tr_atr': atr,
                        'z_score': z_score,
                        'bars': symbol_bars  # Store bars for Kristjan checklist
                    })
                
            except Exception as e:
                print(f"Error processing {symbol}: {e}", file=sys.stderr)
                continue
        
        # Sort by setup score (flag breakouts get slight priority)
        def sort_key(x):
            base_score = x['setup'].score
            # Flag breakouts get +0.1 priority boost
            if x['setup'].setup == "Flag Breakout":
                return base_score + 0.1
            return base_score
        
        setups.sort(key=sort_key, reverse=True)
        
        return setups[:top_n]
        
    except Exception as e:
        print(f"Breakout scan failed: {e}", file=sys.stderr)
        return []

def kristjan_checklist(symbol: str, bars: list, benchmark_bars: list) -> str:
    """
    Kristjan-style breakout checklist with numeric stats, +/- ratings,
    and reference points separated by '/' instead of 'vs'.
    """
    import numpy as np

    closes = np.array([b.close for b in bars], float)
    highs = np.array([b.high for b in bars], float)
    lows  = np.array([b.low for b in bars], float)
    vols  = np.array([b.volume for b in bars], float)

    # --- 1. Price and daily change
    price = closes[-1]
    prev_close = closes[-2]
    pct_change = (price / prev_close - 1) * 100

    # --- 2. ADR (Average Daily Range %)
    adr = np.mean((highs - lows) / lows * 100)
    adr_ref = 5.0
    adr_flag = "+" if adr >= adr_ref else "-"

    # --- 3. Range tightness (last 30 bars)
    base_high = np.max(closes[-30:])
    base_low  = np.min(closes[-30:])
    range_pct = (base_high - base_low) / base_low * 100
    range_ref = 15.0
    tight_flag = "+" if range_pct <= range_ref else "-"

    # --- 4. ATR contraction (14d vs 50d)
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

    # --- 5. Volume expansion
    vol50 = np.mean(vols[-51:-1])
    vol_mult = vols[-1] / vol50 if vol50 > 0 else 1
    vol_flag = "+" if vol_mult >= 1.5 else "-"
    # volume units simplified (millions)
    vol_now_m = vols[-1] / 1e6
    vol_ref_m = vol50 / 1e6

    # --- 6. Relative strength vs benchmark
    bench_close = np.array([b.close for b in benchmark_bars], float)
    rs_ratio = (price / bench_close[-1]) / np.mean(closes[-50:] / bench_close[-50:])
    rs_ref = 1.0
    rs_flag = "+" if rs_ratio > rs_ref else "-"

    # --- 7. Market filter (10/20DMA)
    bench_10 = np.mean(bench_close[-10:])
    bench_20 = np.mean(bench_close[-20:])
    market_flag = "+" if bench_10 > bench_20 else "-"
    market_ref = "10>20"

    # --- 8. Breakout distance from base high
    breakout_pct = (price / base_high - 1) * 100
    breakout_ref = 1.5
    breakout_flag = "+" if breakout_pct >= breakout_ref else "-"

    # --- 9. Flag vs Range breakout (only if all criteria pass)
    prior_window = closes[-60:-30] if len(closes) > 60 else closes[:len(closes)//2]
    prior_leg = (base_low / np.min(prior_window) - 1) * 100 if len(prior_window) > 0 else 0
    
    # Check if this is a valid breakout
    is_valid_breakout = (
        tight_flag == "+" and  # Range tightness
        atr_flag == "+" and    # ATR contraction
        vol_flag == "+" and    # Volume expansion
        rs_flag == "+" and     # Relative strength
        market_flag == "+" and # Market filter
        breakout_flag == "+"   # Breakout distance
    )
    
    # Determine setup type only if valid breakout
    if is_valid_breakout:
        setup_type = "Flag Breakout" if prior_leg >= 30 else "Range Breakout"
    else:
        setup_type = ""

    # --- 10. Compose output
    checklist = (
        f"${symbol} {price:.2f} {pct_change:+.1f}% | "
        f"ADR {adr:.1f}/{adr_ref:.0f}%{adr_flag} | "
        f"Range {range_pct:.1f}/{range_ref:.0f}%{tight_flag} | "
        f"ATR {atr14:.2f}/{atr50:.2f} ({atr_ratio:.2f}×){atr_flag} | "
        f"V {vol_now_m:.1f}M/{vol_ref_m:.1f}M ({vol_mult:.1f}×){vol_flag} | "
        f"RS {rs_ratio:.2f}/{rs_ref:.2f}{rs_flag} | "
        f"M {bench_10:.1f}/{bench_20:.1f} ({market_ref}){market_flag} | "
        f"B {breakout_pct:.1f}/{breakout_ref:.1f}%{breakout_flag}"
    )
    
    # Add setup type only if valid breakout
    if setup_type:
        checklist += f" | {setup_type}"

    return checklist

def format_breakout_signal(symbol, price, change_pct, rs_score, adr_pct, setup_type, rsi=50, tr_atr=1.0, z_score=0.0):
    """Format breakout signal: $SYMBOL $PRICE +X.X% | ## RSI | X.XXx ATR | Z X.X | Flag/Range Breakout"""
    # Format price: no cents for thousands+, with cents for under $1000
    price_str = f"${price:,.0f}" if price >= 1000 else f"${price:,.2f}"
    return f"${symbol} {price_str} {change_pct:+.1f}% | {rsi:.0f} RSI | {tr_atr:.2f}x ATR | Z {z_score:.1f} | {setup_type}"

def main():
    """Main unified breakout scanner with Kristjan checklist format"""
    print("📈 Scanning for breakout setups (flag and range)...", file=sys.stderr)
    
    try:
        # Get benchmark data (SPY) for relative strength calculations
        benchmark_bars = None
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        if api_key and secret_key:
            try:
                client = StockHistoricalDataClient(api_key, secret_key)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)
                
                benchmark_request = StockBarsRequest(
                    symbol_or_symbols="SPY",
                    timeframe=TimeFrame.Day,
                    start=start_date,
                    end=end_date
                )
                
                benchmark_data = client.get_stock_bars(benchmark_request)
                if benchmark_data and "SPY" in benchmark_data.data:
                    benchmark_bars = benchmark_data.data["SPY"]
                    print(f"📊 Loaded {len(benchmark_bars)} SPY bars for benchmark", file=sys.stderr)
            except Exception as e:
                print(f"Warning: Could not load benchmark data: {e}", file=sys.stderr)
        else:
            # Create mock SPY bars for testing
            import random
            benchmark_bars = []
            spy_price = 450.0  # Starting SPY price
            
            for i in range(90):
                change = random.uniform(-0.015, 0.02)  # -1.5% to +2% daily change
                spy_price *= (1 + change)
                
                high = spy_price * random.uniform(1.001, 1.015)
                low = spy_price * random.uniform(0.985, 0.999)
                volume = random.randint(50000000, 150000000)  # SPY volume
                
                class MockBar:
                    def __init__(self, open_price, high_price, low_price, close_price, vol):
                        self.open = open_price
                        self.high = high_price
                        self.low = low_price
                        self.close = close_price
                        self.volume = vol
                
                benchmark_bars.append(MockBar(spy_price, high, low, spy_price, volume))
            
            print(f"📊 Created {len(benchmark_bars)} mock SPY bars for benchmark", file=sys.stderr)
        
        # Get all stocks and show checklist for each (regardless of breakout status)
        if not api_key or not secret_key:
            print("Warning: ALPACA_API_KEY and ALPACA_SECRET_KEY not set, using mock data", file=sys.stderr)
            # Create mock data for testing
            import random
            
            def create_mock_bars(symbol, days=90):
                bars = []
                base_price = 450.25 if symbol == 'NVDA' else 185.50
                current_price = base_price
                
                for i in range(days):
                    # Add some realistic price movement
                    change = random.uniform(-0.02, 0.03)  # -2% to +3% daily change
                    current_price *= (1 + change)
                    
                    high = current_price * random.uniform(1.001, 1.02)
                    low = current_price * random.uniform(0.98, 0.999)
                    volume = random.randint(1000000, 10000000)
                    
                    # Create a mock Bar object
                    class MockBar:
                        def __init__(self, open_price, high_price, low_price, close_price, vol):
                            self.open = open_price
                            self.high = high_price
                            self.low = low_price
                            self.close = close_price
                            self.volume = vol
                    
                    bars.append(MockBar(current_price, high, low, current_price, volume))
                
                return bars
            
            # Show checklist for mock stocks
            mock_symbols = ['NVDA', 'AAPL', 'MSFT', 'GOOGL', 'TSLA']
            for symbol in mock_symbols:
                symbol_bars = create_mock_bars(symbol)
                if benchmark_bars:
                    signal = kristjan_checklist(symbol, symbol_bars, benchmark_bars)
                    print(signal)
            return
        
        # Get liquid stocks
        symbols = get_liquid_stocks()
        
        print(f"📊 Analyzing {len(symbols)} stocks from filtered universe...", file=sys.stderr)
        
        for symbol in symbols:  # Analyze all filtered dynamic stocks
            try:
                # Get daily bars for last 3 months
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)
                
                request = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=TimeFrame.Day,
                    start=start_date,
                    end=end_date
                )
                
                bars = client.get_stock_bars(request)
                
                if not bars or symbol not in bars.data:
                    continue
                
                symbol_bars = bars.data[symbol]
                if len(symbol_bars) < 30:
                    continue
                
                # Show checklist for this stock
                if benchmark_bars:
                    signal = kristjan_checklist(symbol, symbol_bars, benchmark_bars)
                    print(signal)
                
            except Exception as e:
                print(f"Error processing {symbol}: {e}", file=sys.stderr)
                continue
            
    except Exception as e:
        print(f"Breakout scan failed: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
