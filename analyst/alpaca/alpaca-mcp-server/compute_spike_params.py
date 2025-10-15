#!/usr/bin/env python3
"""
Crypto volatility signal detection using Alpaca API.
Long-only entry signals with quant-style formatting.
"""
import os
import sys
import math
from datetime import datetime, timedelta
from statistics import mean, pstdev
import numpy as np
from dotenv import load_dotenv
from alpaca.data.historical.crypto import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient

load_dotenv()

# === 5-MIN BAR TUNING (stocks & crypto) ===
THRESHOLDS = {
    "stocks": {
        # Base breakout gates (tight)
        "breakout_tr_atr": 2.0,   # TR/ATR > 2.0
        "breakout_z": 2.5,        # |Z| > 2.5
        "breakout_dp": 0.03,      # |ΔP| > 3% (decimal 0.03)
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

    "crypto": {
        # Same base gates for 5m crypto
        "breakout_tr_atr": 2.0,
        "breakout_z": 2.0,
        "breakout_dp": 0.02,
        "use_geq": False,

        # No exchange "cash open"
        "mute_first_minutes": 0,

        # Intrabar confirmations (slightly looser retrace for noise)
        "persistence_bars": 2,
        "follow_through_dp": 0.006,   # +0.60%
        "retrace_cap_dp": 0.003,      # 0.30%

        # VWAP confirmation
        "vwap_disp_dp": 0.005,        # +0.50%
        "vwap_slope_min_dp": 0.000,   # disabled

        # Gap-like (only if you emulate sessions)
        "gap_threshold": 0.04,
        "gap_follow_through_dp": 0.008,
        "gap_retrace_cap_dp": 0.003,

        # Exit (slightly looser for crypto noise)
        "exit_min_vwap_disp_dp": 0.0025,
        "exit_backslide_dp": 0.004,
        "exit_retrace_breach_dp": 0.005,
        "exit_persist_window": 3,
        "exit_neg_bars": 2,
        "exit_z_floor": 1.0,
        "exit_tratr_floor": None,
        "exit_score_min": 2,

        "early_minutes": 0,
        "early_breakout_tr_atr": None,
        "early_breakout_z": None,
        "early_breakout_dp": None,
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

        return "Breakout"

# === QUANT FORMATTER (L/E) ===
def format_signal_line(
    symbol: str,
    price: float,
    dpp: float,
    tr_atr: float,
    z: float,
    code: str | None,
    *,
    vwap_disp: float | None = None,
) -> str:
    """Quant-style compact format: $SYMBOL $PRICE ±X.XX% | 4.73x ATR | Z 8.82 | VW+0.45 | Breakout"""
    # Format price: no cents for thousands+, with cents for under $1000
    price_str = f"${price:,.0f}" if price >= 1000 else f"${price:,.2f}"
    line = f"${symbol} {price_str} {dpp:+.2f}% | {tr_atr:.2f}x ATR | Z {z:.2f}"
    if vwap_disp is not None:
        line += f" | VW{vwap_disp:+.2f}"
    if code is not None:
        line += f" | {code}"
    return line

def get_major_cryptos():
    """Dynamically fetch major cryptocurrencies from Alpaca API."""
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    trading_client = TradingClient(api_key, secret_key, paper=True)
    
    majors = []
    try:
        assets = trading_client.get_all_assets()
        for asset in assets:
            # Check if crypto, active, and major
            if (getattr(asset, 'asset_class', None) == 'crypto' and 
                getattr(asset, 'status', None) == 'active' and
                getattr(asset, 'tradable', False)):
                
                # Check if it's a major crypto (has is_major attribute or high liquidity indicators)
                is_major = getattr(asset, 'is_major', None)
                fractionable = getattr(asset, 'fractionable', False)
                
                # If is_major exists, use it; otherwise use fractionable as proxy for major
                if is_major or (is_major is None and fractionable):
                    sym = asset.symbol
                    # Normalize symbol format to BASE/USD
                    if sym.endswith('USD') and '/' not in sym:
                        base = sym[:-3]
                        majors.append(f"{base}/USD")
                    elif '/' in sym and sym.endswith('/USD'):
                        majors.append(sym)
    except Exception as e:
        print(f"Warning: Could not fetch major cryptos dynamically: {e}", file=sys.stderr)
        # Fallback to hardcoded list
        return ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "DOGE/USD", "ADA/USD", 
                "AVAX/USD", "LTC/USD", "DOT/USD", "LINK/USD", "UNI/USD", "ATOM/USD"]
    
    return sorted(set(majors))

def main():
    """Main entry point."""
    crypto_client = CryptoHistoricalDataClient(os.getenv('ALPACA_API_KEY'), os.getenv('ALPACA_SECRET_KEY'))
    now = datetime.now()
    
    # Dynamically fetch major cryptos
    symbols_list = get_major_cryptos()
    print(f"Scanning {len(symbols_list)} major cryptos...", file=sys.stderr)
    
    # Fetch 5-min bars for last 24 hours
    start_24h = now - timedelta(hours=24)
    request = CryptoBarsRequest(symbol_or_symbols=symbols_list, timeframe=TimeFrame(5, TimeFrameUnit.Minute), start=start_24h, end=now)
    bars_dict = crypto_client.get_crypto_bars(request).data
    
    signals = []
    for sym in symbols_list:
        # Exclude stablecoins
        base = sym.split('/')[0]
        if base in ['USDC', 'USDG']:
            continue
        
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
        
        # Classify
        sig = classify_long_entry(tr_atr, z, dpp, "crypto")
        base = sym.split('/')[0]
        signal_line = format_signal_line(base, closes[-1], dpp, tr_atr, z, sig)
        signals.append((closes[-1], signal_line))  # Store with price for sorting
    
    # Sort by price descending and print
    signals.sort(key=lambda x: x[0], reverse=True)
    for _, s in signals:
        print(s)

if __name__ == "__main__":
    main()
