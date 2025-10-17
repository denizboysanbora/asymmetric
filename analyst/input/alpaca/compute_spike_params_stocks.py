#!/usr/bin/env python3
"""
Stock volatility signal detection using Alpaca API.
Long-only entry signals with quant-style formatting.
"""
import os
import sys
import math
from datetime import datetime, timedelta
from statistics import mean, pstdev
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass, AssetStatus

load_dotenv()

# Major ETFs to always include (exceptions to ETF exclusion rule)
ALWAYS_INCLUDE = ["SPY", "QQQ", "GLD"]

# === 5-MIN BAR TUNING (stocks & crypto) ===
THRESHOLDS = {
    "stocks": {
        # Base breakout gates (tight)
        "breakout_tr_atr": 2.0,   # TR/ATR > 2.0
        "breakout_z": 2.0,        # |Z| > 2.0
        "breakout_dp": 0.02,      # |ΔP| > 2% (decimal 0.02)
        "use_geq": False,

        # Ignore the open
        "mute_first_minutes": 30,     # ignore first 30 min (6×5m bars)

        # Stronger gates for the first hour (from 30 to 60 minutes after open)
        "early_minutes": 60,          # apply when 30 <= minutes_since_open < 60
        "early_breakout_tr_atr": 2.2,
        "early_breakout_z": 3.5,
        "early_breakout_dp": 0.04,    # 4%

        # Intrabar confirmations for entry (optional; pass inputs to enable)
        "persistence_bars": 3,        # last N bars positive (0 disables)
        "follow_through_dp": 0.006,   # ≥ +0.60% additional progress shortly after
        "retrace_cap_dp": 0.0025,     # ≤ 0.25% worst pullback

        # VWAP confirmation for entry (tight)
        "vwap_disp_dp": 0.007,        # price ≥ +0.70% above VWAP
        "vwap_slope_min_dp": 0.001,   # VWAP slope ≥ +0.10% per 5m

        # Gap control for entry (optional if you pass prev_close & open_price)
        "gap_threshold": 0.04,        # ≥ +4% gap-up requires stricter conf
        "gap_follow_through_dp": 0.007,  # +0.70% extra progress
        "gap_retrace_cap_dp": 0.002,     # ≤ 0.20% retrace

        # === EXHAUSTION EXIT (when already LONG) ===
        "exit_min_vwap_disp_dp": 0.003,   # 0.30% above VWAP required; else score +1 (or if ≤ 0)
        "exit_backslide_dp": 0.003,       # -0.30% forward move (down) → score +1
        "exit_retrace_breach_dp": 0.004,  # 0.40% pullback breach → score +1
        "exit_persist_window": 3,         # lookback bars for persistence flip
        "exit_neg_bars": 2,               # need at least 2 negative bars in window → score +1
        "exit_z_floor": 1.0,              # z ≤ +1.0 AND dpp ≤ 0 → score +1
        "exit_tratr_floor": None,         # e.g., 1.5 to require sustained energy; None disables
        "exit_score_min": 2,              # require at least 2 conditions to fire exit
    },

}

def _cmp(x: float, thresh: float, geq: bool) -> bool:
    return (x >= thresh) if geq else (x > thresh)

def _finite(*vals) -> bool:
    return all(map(math.isfinite, vals))

# === ENTRY: Momentum Long only ===
def classify_long_entry(
    tr_atr: float,
    z: float,
    dpp: float,
    asset: str = "stocks",
    *,
    minutes_since_open = None,
    prev_close = None,
    open_price = None,
    recent_dpp = None,
    fut_move_dpp = None,
    fut_retrace_dpp = None,
    vwap_disp_dpp = None,
    vwap_slope_dpp = None,
):
    """Returns: "L" for a new Long entry, or None."""
    if not _finite(tr_atr, z, dpp):
        return None

    cfg = THRESHOLDS.get(asset.lower(), THRESHOLDS["stocks"])
    geq = bool(cfg.get("use_geq", False))

    # Mute the open
    mute_n = int(cfg.get("mute_first_minutes", 0))
    if mute_n and minutes_since_open is not None and minutes_since_open < mute_n:
        return None

    # % → decimals
    dp = dpp / 100.0
    ft = None if fut_move_dpp is None else (fut_move_dpp / 100.0)
    rt = None if fut_retrace_dpp is None else (fut_retrace_dpp / 100.0)
    vw = None if vwap_disp_dpp is None else (vwap_disp_dpp / 100.0)
    vws = None if vwap_slope_dpp is None else (vwap_slope_dpp / 100.0)

    # Early-session stronger gates (between mute and early_minutes)
    b_tratr = cfg["breakout_tr_atr"]
    b_z     = cfg["breakout_z"]
    b_dp    = cfg["breakout_dp"]

    early_mins = int(cfg.get("early_minutes", 0))
    if (
        early_mins
        and minutes_since_open is not None
        and minutes_since_open < early_mins
        and (mute_n == 0 or minutes_since_open >= mute_n)
    ):
        b_tratr = cfg.get("early_breakout_tr_atr", b_tratr) or b_tratr
        b_z     = cfg.get("early_breakout_z", b_z)         or b_z
        b_dp    = cfg.get("early_breakout_dp", b_dp)       or b_dp

    # Base momentum gates (long only)
    vol_ok = _cmp(tr_atr, b_tratr, geq)
    mag_ok = _cmp(abs(z), b_z, geq) and _cmp(abs(dp), b_dp, geq)
    same_sign_pos = (z > 0) and (dp > 0)
    long_base  = vol_ok and mag_ok and same_sign_pos
    if not long_base:
        return None

    # Gap control
    gap_thr = cfg.get("gap_threshold")
    if gap_thr is not None and prev_close and open_price:
        gap_pct = (open_price / prev_close - 1.0)  # decimal
        if gap_pct >= gap_thr:
            g_ft = cfg.get("gap_follow_through_dp")
            g_rt = cfg.get("gap_retrace_cap_dp")
            if (ft is None) or not (ft > 0 and _cmp(abs(ft), g_ft, True)): return None
            if (rt is not None) and not (rt <= 0 and abs(rt) <= g_rt):     return None

    # Persistence
    n_pers = int(cfg.get("persistence_bars", 0))
    if n_pers > 0 and recent_dpp:
        tail = recent_dpp[-n_pers:]
        if len(tail) == n_pers and not all((x is not None) and (x > 0) for x in tail):
            return None

    # Follow-through & retrace caps
    ft_thr = cfg.get("follow_through_dp")
    if ft_thr is not None and ft is not None:
        if not (ft > 0 and _cmp(abs(ft), ft_thr, True)):
            return None
    rt_cap = cfg.get("retrace_cap_dp")
    if rt_cap is not None and rt is not None:
        if not (rt <= 0 and abs(rt) <= rt_cap):
            return None

    # VWAP displacement + slope
    vwap_req = cfg.get("vwap_disp_dp")
    if vwap_req is not None and vw is not None:
        if not (vw > 0 and _cmp(abs(vw), vwap_req, True)):
            return None
    vws_min = cfg.get("vwap_slope_min_dp")
    if vws_min is not None and vws is not None and vws_min > 0:
        if not (vws > 0 and abs(vws) >= vws_min):
            return None

        return "Volatility"

# === QUANT FORMATTER (L/E) ===
def calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
    """Calculate RSI (Relative Strength Index) for given price array."""
    if len(prices) < period + 1:
        return 50.0  # Default neutral RSI if not enough data
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    # Calculate average gains and losses using Wilder's smoothing
    avg_gains = np.mean(gains[:period])
    avg_losses = np.mean(losses[:period])
    
    for i in range(period, len(gains)):
        avg_gains = (avg_gains * (period - 1) + gains[i]) / period
        avg_losses = (avg_losses * (period - 1) + losses[i]) / period
    
    if avg_losses == 0:
        return 100.0
    
    rs = avg_gains / avg_losses
    rsi = 100 - (100 / (1 + rs))
    return rsi

def format_signal_line(
    symbol: str,
    price: float,
    dpp: float,
    tr_atr: float,
    z: float,
    rsi: float,
    code: str | None,
    *,
    vwap_disp: float | None = None,
    rs_score: float = 0.5,
    adr_pct: float = 2.0,
) -> str:
    """Updated format: $SYMBOL $PRICE ±X.X% | ##/## RSI | X ATR | Z X.X | ADR X% | NAME"""
    # Format price: no cents for thousands+, with cents for under $1000
    price_str = f"${price:,.0f}" if price >= 1000 else f"${price:,.2f}"
    # Convert RS score to percentage (0-1 -> 0-100)
    rs_percent = rs_score * 100
    # Round ATR to integer
    atr_int = round(tr_atr)
    # Round ADR to integer percentage
    adr_int = round(adr_pct)
    line = f"${symbol} {price_str} {dpp:+.1f}% | {rsi:.0f}/{rs_percent:.0f} RSI | {atr_int} ATR | Z {z:.1f} | ADR {adr_int}%"
    if vwap_disp is not None:
        line += f" | VW{vwap_disp:+.2f}"
    if code is not None:
        line += f" | {code}"
    return line

def get_liquid_stocks():
    """Dynamically fetch liquid stocks from Alpaca API."""
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    trading_client = TradingClient(api_key, secret_key, paper=True)
    
    # Keywords to filter out ETFs and leveraged products
    etf_keywords = ['ETF', 'Trust', 'Fund', 'Index']
    leveraged_keywords = ['Ultra', '2x', '3x', 'Bull', 'Bear', 'Inverse', 'Short', 'Leveraged', 'ProShares', 'Direxion', 'Daily']
    
    liquid_stocks = []
    try:
        assets = trading_client.get_all_assets()
        for asset in assets:
            # Ultra-liquid filters: has_options + 30% margin + NYSE/NASDAQ only
            if (str(getattr(asset, 'asset_class', None)) == 'AssetClass.US_EQUITY' and 
                str(getattr(asset, 'status', None)) == 'AssetStatus.ACTIVE' and
                getattr(asset, 'tradable', False) and
                getattr(asset, 'fractionable', False) and
                getattr(asset, 'marginable', False) and
                getattr(asset, 'easy_to_borrow', False) and
                getattr(asset, 'shortable', False) and
                getattr(asset, 'maintenance_margin_requirement', None) == 30.0 and
                str(getattr(asset, 'exchange', '')) in ['AssetExchange.NYSE', 'AssetExchange.NASDAQ']):
                
                # Check if has options
                attributes = getattr(asset, 'attributes', []) or []
                if 'has_options' in attributes:
                    # Filter out ETFs and leveraged products
                    name = getattr(asset, 'name', '') or ''
                    is_etf = any(keyword in name for keyword in etf_keywords)
                    is_leveraged = any(keyword in name for keyword in leveraged_keywords)
                    
                    if not is_etf and not is_leveraged:
                        liquid_stocks.append(asset.symbol)
    except Exception as e:
        print(f"Warning: Could not fetch liquid stocks dynamically: {e}", file=sys.stderr)
        # Fallback to a basic list (stocks only, no ETFs)
        return sorted(set(["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "NFLX", "INTC"] + ALWAYS_INCLUDE))
    
    # Always include major ETFs (SPY, QQQ, GLD) regardless of filters
    all_symbols = sorted(set(liquid_stocks + ALWAYS_INCLUDE))
    return all_symbols

def main():
    """Main entry point."""
    stock_client = StockHistoricalDataClient(os.getenv('ALPACA_API_KEY'), os.getenv('ALPACA_SECRET_KEY'))
    now = datetime.now()
    
    # Optional single-symbol override via CLI: --symbol TSLA
    symbol_override = None
    if len(sys.argv) >= 3 and sys.argv[1] == '--symbol':
        symbol_override = sys.argv[2].upper().strip()

    # Get liquid stocks dynamically (or override)
    stock_symbols = [symbol_override] if symbol_override else get_liquid_stocks()
    print(f"Scanning {len(stock_symbols)} stocks...", file=sys.stderr)
    
    # Fetch 5-min bars for last 24 hours (use default feed - works with free tier)
    start_24h = now - timedelta(hours=24)
    request = StockBarsRequest(symbol_or_symbols=stock_symbols, timeframe=TimeFrame(5, TimeFrameUnit.Minute), start=start_24h, end=now)
    bars_dict = stock_client.get_stock_bars(request).data
    
    signals = []
    for sym in stock_symbols:
        bars = bars_dict.get(sym, [])
        if len(bars) < 20:
            continue
        
        # Calculate metrics
        closes = np.array([float(b.close) for b in bars])
        rets = np.diff(np.log(closes))
        
        if len(rets) < 2:
            continue
        
        # TR/ATR
        tr_vals = []
        prev_close = float(bars[0].open)
        for b in bars:
            hi, lo, cl = float(b.high), float(b.low), float(b.close)
            tr = max(hi - lo, abs(hi - prev_close), abs(lo - prev_close))
            tr_vals.append(tr)
            prev_close = cl
        
        alpha = 2.0 / 15.0
        ema = None
        for tr in tr_vals:
            ema = tr if ema is None else alpha * tr + (1 - alpha) * ema
        tr_atr = tr_vals[-1] / ema if ema > 0 else float('nan')
        
        # Z-score
        mu = float(np.mean(rets[:-1]))
        sd = float(np.std(rets[:-1], ddof=1)) if len(rets) > 2 else float(np.std(rets[:-1]))
        z = (float(rets[-1]) - mu) / sd if sd > 1e-12 else 0.0
        
        # Price change
        dpp = ((closes[-1] - closes[0]) / closes[0]) * 100.0
        
        # Calculate RSI
        rsi = calculate_rsi(closes)
        
        # Calculate RS score (simplified - using price momentum vs SPY)
        rs_score = 0.5  # Default neutral RS
        if len(closes) >= 20:
            # Simple RS calculation: stock performance vs market
            stock_return = (closes[-1] - closes[-20]) / closes[-20]
            rs_score = max(0.0, min(1.0, (stock_return + 0.1) / 0.2))  # Normalize to 0-1
        
        # Calculate ADR (Average Daily Range)
        adr_pct = 2.0  # Default ADR
        if len(closes) >= 20:
            daily_ranges = []
            for i in range(1, min(20, len(closes))):
                daily_range = abs(closes[i] - closes[i-1]) / closes[i-1]
                daily_ranges.append(daily_range)
            if daily_ranges:
                adr_pct = np.mean(daily_ranges) * 100
        
        # Classify
        sig = classify_long_entry(tr_atr, z, dpp, "stocks")
        
        # Determine signal type
        signal_type = "Volatility" if sig == "Volatility" else "Momentum"
        
        # Updated format: $SYMBOL $PRICE +X.XX% | ## RSI | X.XXx ATR | Z X.XX | ## RS | ADR X.X% | NAME
        signal_line = format_signal_line(sym, closes[-1], dpp, tr_atr, z, rsi, signal_type, rs_score=rs_score, adr_pct=adr_pct)
        signals.append(signal_line)
    
    for s in signals:
        print(s)

if __name__ == "__main__":
    main()
