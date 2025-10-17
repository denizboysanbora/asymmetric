"""
Setup detection for Qullamaggie.
Detects and labels the three timeless momentum setups.
"""
from typing import List, Dict, Literal, Optional, Tuple
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field
from loguru import logger

from .features import (
    ema, adr_pct, rs_score, detect_explosive_leg, detect_flag_tightening,
    calculate_atr
)
from .config import Config


class SetupTag(BaseModel):
    """Setup tag model."""
    setup: Literal[
        "Qullamaggie Breakout",
        "Qullamaggie Episodic Pivot", 
        "Qullamaggie Parabolic Long"
    ] = Field(..., description="Setup type")
    triggered: bool = Field(..., description="Whether setup is triggered")
    score: float = Field(..., description="Setup strength score (0-1)")
    meta: Dict = Field(default_factory=dict, description="Setup-specific metadata")
    
    class Config:
        extra = "allow"


def detect_breakout(
    daily_df: pd.DataFrame,
    cfg: Config,
    symbol: str
) -> Optional[SetupTag]:
    """
    Detect Qullamaggie Breakout setup.
    
    Criteria:
    - Prior impulse of 30-100%+ within last 1-3 months
    - Tight flag consolidation (5-40 days) with higher lows, contracting ATR
    - Price surfing rising 10/20-day MAs
    - ADR ≥ 5%, RS in top decile
    
    Args:
        daily_df: Daily bars DataFrame with MultiIndex [symbol, date]
        cfg: Configuration object
        symbol: Stock symbol
        
    Returns:
        SetupTag if breakout detected, None otherwise
    """
    try:
        symbol_data = daily_df.xs(symbol, level=0)
        
        if len(symbol_data) < cfg.setups.breakout.lookback_impulse_days:
            return None
        
        # Check for prior impulse (30-100%+ within last 1-3 months)
        impulse_detected = False
        impulse_pct = 0
        impulse_start = None
        impulse_end = None
        
        # Look for big moves in the last 60 days
        recent_data = symbol_data.tail(cfg.setups.breakout.lookback_impulse_days)
        
        for i in range(10, len(recent_data) - 10):  # Need space for swing low/high
            window_data = recent_data.iloc[i-10:i+10]
            swing_low = window_data['low'].min()
            swing_high = window_data['high'].max()
            
            if swing_high > swing_low:
                move_pct = (swing_high - swing_low) / swing_low
                if move_pct >= cfg.setups.breakout.impulse_min_pct / 100:
                    impulse_detected = True
                    impulse_pct = move_pct * 100
                    impulse_start = window_data['low'].idxmin()
                    impulse_end = window_data['high'].idxmax()
                    break
        
        if not impulse_detected:
            return None
        
        # Check for tight flag consolidation after impulse
        flag_start = impulse_end
        flag_data = symbol_data.loc[flag_start:]
        
        if len(flag_data) < cfg.setups.breakout.flag_min_days:
            return None
        
        # Limit flag analysis to max days
        if len(flag_data) > cfg.setups.breakout.flag_max_days:
            flag_data = flag_data.tail(cfg.setups.breakout.flag_max_days)
        
        # Check for higher lows
        lows = flag_data['low']
        higher_lows = 0
        for i in range(1, len(lows)):
            if lows.iloc[i] > lows.iloc[i-1]:
                higher_lows += 1
        
        if higher_lows < 2:  # Need at least 2 higher lows
            return None
        
        # Check ATR contraction (simplified calculation)
        high = flag_data['high']
        low = flag_data['low']
        close = flag_data['close']
        
        # True Range components
        high_low = high - low
        high_close_prev = np.abs(high - close.shift())
        low_close_prev = np.abs(low - close.shift())
        
        # True Range
        true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        
        # ATR as rolling mean of True Range
        atr = true_range.rolling(window=14, min_periods=7).mean()
        
        if len(atr.dropna()) < 10:
            return None
        
        recent_atr = atr.tail(5).mean()
        baseline_atr = atr.iloc[:len(atr)//2].mean()
        
        atr_contraction = recent_atr / baseline_atr if baseline_atr > 0 else 1
        
        if atr_contraction > cfg.setups.breakout.atr_contract_ratio:
            return None
        
        # Check if price is surfing rising 10/20-day MAs
        close_prices = flag_data['close']
        ema_10 = ema(close_prices, 10)
        ema_20 = ema(close_prices, 20)
        
        if len(ema_10) < 3 or len(ema_20) < 3:
            return None
        
        # Check if EMAs are rising and price is above them
        ema_10_rising = ema_10.iloc[-1] > ema_10.iloc[-3]
        ema_20_rising = ema_20.iloc[-1] > ema_20.iloc[-3]
        price_above_emas = close_prices.iloc[-1] > ema_10.iloc[-1] and close_prices.iloc[-1] > ema_20.iloc[-1]
        
        if not (ema_10_rising and ema_20_rising and price_above_emas):
            return None
        
        # Calculate setup score
        flag_days = len(flag_data)
        score = min(impulse_pct / 100, 1.0) * 0.4 + (1 - atr_contraction) * 0.3 + (higher_lows / flag_days) * 0.3
        
        meta = {
            "impulse_pct": impulse_pct,
            "flag_days": flag_days,
            "atr_contraction": atr_contraction,
            "higher_lows_count": higher_lows,
            "ema_10_rising": ema_10_rising,
            "ema_20_rising": ema_20_rising,
            "price_above_emas": price_above_emas,
            "impulse_start": impulse_start.isoformat() if impulse_start else None,
            "impulse_end": impulse_end.isoformat() if impulse_end else None
        }
        
        return SetupTag(
            setup="Qullamaggie Breakout",
            triggered=False,  # Will be updated by opening range analysis
            score=score,
            meta=meta
        )
        
    except Exception as e:
        logger.error(f"Error detecting breakout for {symbol}: {e}")
        return None


def detect_ep(
    daily_df: pd.DataFrame,
    premarket_df: pd.DataFrame,
    minute_df: Optional[pd.DataFrame],
    cfg: Config,
    symbol: str
) -> Optional[SetupTag]:
    """
    Detect Qullamaggie Episodic Pivot setup.
    
    Criteria:
    - Gap ≥ 10% over prior close
    - Big volume (premarket notional ≥ 2M OR first 10 min volume several × avg)
    - Prefer flat prior 3-6 months (not extended)
    - ADR ≥ 5%
    
    Args:
        daily_df: Daily bars DataFrame
        premarket_df: Premarket stats DataFrame
        minute_df: Intraday minute bars (optional)
        cfg: Configuration object
        symbol: Stock symbol
        
    Returns:
        SetupTag if EP detected, None otherwise
    """
    try:
        symbol_data = daily_df.xs(symbol, level=0)
        
        if len(symbol_data) < 126:  # Need 6 months of data
            return None
        
        # Check for gap
        symbol_premarket = premarket_df[premarket_df['symbol'] == symbol]
        if symbol_premarket.empty:
            return None
        
        gap_pct = symbol_premarket.iloc[0]['gap_pct']
        if gap_pct < cfg.setups.ep.gap_min_pct:
            return None
        
        # Check premarket volume
        premkt_notional = symbol_premarket.iloc[0].get('premkt_notional', 0)
        if premkt_notional < cfg.setups.ep.premkt_notional_min:
            # Check early volume if premarket volume insufficient
            if minute_df is not None:
                symbol_minute = minute_df.xs(symbol, level='symbol') if symbol in minute_df.index.get_level_values('symbol') else None
                if symbol_minute is not None:
                    # Check first 10 minutes volume vs average
                    early_volume = symbol_minute.head(cfg.setups.ep.require_big_volume_minutes)['volume'].sum()
                    avg_daily_volume = symbol_data['volume'].tail(20).mean()
                    volume_ratio = early_volume / avg_daily_volume if avg_daily_volume > 0 else 0
                    
                    if volume_ratio < 2.0:  # Need at least 2x average daily volume in first 10 min
                        return None
                else:
                    return None
            else:
                return None
        
        # Check for flat prior 3-6 months (not extended)
        if cfg.setups.ep.prefer_flat_prior_months:
            prior_6m = symbol_data.tail(126)  # 6 months
            prior_3m = symbol_data.tail(63)   # 3 months
            
            # Calculate returns over prior periods
            return_6m = (prior_6m['close'].iloc[-1] - prior_6m['close'].iloc[0]) / prior_6m['close'].iloc[0]
            return_3m = (prior_3m['close'].iloc[-1] - prior_3m['close'].iloc[0]) / prior_3m['close'].iloc[0]
            
            # If stock already had big moves in prior periods, it's not "neglected"
            if return_6m > 0.5 or return_3m > 0.3:  # 50% in 6m or 30% in 3m
                return None
        
        # Calculate setup score
        score = min(gap_pct / 20, 1.0) * 0.6  # Gap contribution (max at 20%)
        
        if premkt_notional >= cfg.setups.ep.premkt_notional_min:
            score += 0.4  # Full volume credit
        elif minute_df is not None:
            # Partial credit for early volume
            symbol_minute = minute_df.xs(symbol, level='symbol') if symbol in minute_df.index.get_level_values('symbol') else None
            if symbol_minute is not None:
                early_volume = symbol_minute.head(cfg.setups.ep.require_big_volume_minutes)['volume'].sum()
                avg_daily_volume = symbol_data['volume'].tail(20).mean()
                volume_ratio = early_volume / avg_daily_volume if avg_daily_volume > 0 else 0
                score += min(volume_ratio / 5, 0.4)  # Max 0.4 for volume
        
        meta = {
            "gap_pct": gap_pct,
            "premkt_notional": premkt_notional,
            "flatness_score": 1.0 if cfg.setups.ep.prefer_flat_prior_months else 0.0,
            "return_6m": return_6m if cfg.setups.ep.prefer_flat_prior_months else None,
            "return_3m": return_3m if cfg.setups.ep.prefer_flat_prior_months else None
        }
        
        return SetupTag(
            setup="Qullamaggie Episodic Pivot",
            triggered=False,  # Will be updated by opening range analysis
            score=score,
            meta=meta
        )
        
    except Exception as e:
        logger.error(f"Error detecting EP for {symbol}: {e}")
        return None


def detect_parabolic_long(
    daily_df: pd.DataFrame,
    cfg: Config,
    symbol: str
) -> Optional[SetupTag]:
    """
    Detect Qullamaggie Parabolic Long setup.
    
    Criteria:
    - Recent drop ≥ 50-60% in ≤ 5 days
    - Oversold: price ≥ 2× ATR below 10/20-day EMA band
    - ADR ≥ 10%
    
    Args:
        daily_df: Daily bars DataFrame
        cfg: Configuration object
        symbol: Stock symbol
        
    Returns:
        SetupTag if parabolic long detected, None otherwise
    """
    try:
        symbol_data = daily_df.xs(symbol, level=0)
        
        if len(symbol_data) < cfg.setups.parabolic_long.lookback_days + 20:
            return None
        
        # Check for recent crash (50-60%+ in ≤ 7 days)
        recent_data = symbol_data.tail(cfg.setups.parabolic_long.lookback_days)
        
        # Find highest point in lookback period
        high_point = recent_data['high'].max()
        high_idx = recent_data['high'].idxmax()
        
        # Find lowest point after high
        after_high = recent_data.loc[high_idx:]
        if len(after_high) < 2:
            return None
        
        low_point = after_high['low'].min()
        low_idx = after_high['low'].idxmin()
        
        # Calculate drawdown
        drawdown_pct = (high_point - low_point) / high_point * 100
        
        if drawdown_pct < cfg.setups.parabolic_long.crash_min_pct:
            return None
        
        # Check if current price is oversold (2× ATR below EMA band)
        current_price = symbol_data['close'].iloc[-1]
        close_prices = symbol_data['close'].tail(20)
        
        ema_10 = ema(close_prices, 10)
        ema_20 = ema(close_prices, 20)
        
        if len(ema_10) < 10 or len(ema_20) < 10:
            return None
        
        # Calculate ATR (simplified calculation)
        high = symbol_data['high']
        low = symbol_data['low']
        close = symbol_data['close']
        
        # True Range components
        high_low = high - low
        high_close_prev = np.abs(high - close.shift())
        low_close_prev = np.abs(low - close.shift())
        
        # True Range
        true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        
        # ATR as rolling mean of True Range
        atr = true_range.rolling(window=14, min_periods=7).mean()
        
        if len(atr.dropna()) == 0:
            return None
        
        current_atr = atr.iloc[-1]
        
        # Check ADR requirement (≥10% for Parabolic Long)
        overall_adr = adr_pct(daily_df, window=20).get(symbol, np.nan)
        if np.isnan(overall_adr) or overall_adr < 10.0:
            return None
        
        # Check oversold condition
        ema_band_low = min(ema_10.iloc[-1], ema_20.iloc[-1])
        atr_distance = (ema_band_low - current_price) / current_atr if current_atr > 0 else 0
        
        if atr_distance < cfg.setups.parabolic_long.oversold_atr_multiple:
            return None
        
        # Check if we're seeing early signs of rebound
        rebound_signal = False
        if len(symbol_data) >= 2:
            # Look for first green candle or higher low
            last_close = symbol_data['close'].iloc[-1]
            prev_close = symbol_data['close'].iloc[-2]
            last_low = symbol_data['low'].iloc[-1]
            prev_low = symbol_data['low'].iloc[-2]
            
            if last_close > prev_close or last_low > prev_low:
                rebound_signal = True
        
        # Calculate setup score
        score = min(drawdown_pct / 80, 1.0) * 0.5 + (atr_distance / 3) * 0.3 + (0.2 if rebound_signal else 0)
        
        meta = {
            "drawdown_pct": drawdown_pct,
            "atr_distance": atr_distance,
            "rebound_signal": rebound_signal,
            "crash_start": high_idx.isoformat() if high_idx else None,
            "crash_end": low_idx.isoformat() if low_idx else None,
            "high_point": high_point,
            "low_point": low_point,
            "current_price": current_price,
            "ema_band_low": ema_band_low
        }
        
        return SetupTag(
            setup="Qullamaggie Parabolic Long",
            triggered=rebound_signal,
            score=score,
            meta=meta
        )
        
    except Exception as e:
        logger.error(f"Error detecting parabolic long for {symbol}: {e}")
        return None


def detect_all_setups(
    daily_df: pd.DataFrame,
    premarket_df: pd.DataFrame,
    minute_df: Optional[pd.DataFrame],
    cfg: Config,
    symbol: str
) -> List[SetupTag]:
    """
    Detect all applicable setups for a symbol.
    
    Args:
        daily_df: Daily bars DataFrame
        premarket_df: Premarket stats DataFrame
        minute_df: Intraday minute bars (optional)
        cfg: Configuration object
        symbol: Stock symbol
        
    Returns:
        List of detected SetupTag objects
    """
    setups = []
    
    # Detect Breakout
    breakout = detect_breakout(daily_df, cfg, symbol)
    if breakout:
        setups.append(breakout)
    
    # Detect EP
    ep = detect_ep(daily_df, premarket_df, minute_df, cfg, symbol)
    if ep:
        setups.append(ep)
    
    # Detect Parabolic Long
    parabolic_long = detect_parabolic_long(daily_df, cfg, symbol)
    if parabolic_long:
        setups.append(parabolic_long)
    
    return setups


def rank_setups(setups: List[SetupTag]) -> List[SetupTag]:
    """
    Rank setups by priority: EP > Breakout > Parabolic Long.
    
    Args:
        setups: List of SetupTag objects
        
    Returns:
        Ranked list of SetupTag objects
    """
    priority_order = {
        "Qullamaggie Episodic Pivot": 1,
        "Qullamaggie Breakout": 2,
        "Qullamaggie Parabolic Long": 3
    }
    
    return sorted(setups, key=lambda s: (priority_order.get(s.setup, 999), -s.score))
