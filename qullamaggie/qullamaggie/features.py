"""
Feature engineering for Qullamaggie.
Provides vectorized helpers for technical analysis and pattern detection.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from loguru import logger


def ema(series: pd.Series, span: int) -> pd.Series:
    """
    Calculate exponential moving average.
    
    Args:
        series: Price series
        span: EMA span
        
    Returns:
        EMA series
    """
    return series.ewm(span=span, adjust=False).mean()


def adr_pct(daily_df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Calculate Average Daily Range percentage for each symbol.
    
    Args:
        daily_df: DataFrame with MultiIndex [symbol, date] and OHLCV columns
        window: Rolling window for ADR calculation
        
    Returns:
        Series with ADR percentage per symbol
    """
    # Calculate daily range percentage
    daily_range = (daily_df['high'] - daily_df['low']) / daily_df['close']
    daily_range_pct = daily_range * 100
    
    # Calculate rolling mean ADR
    adr = daily_range_pct.groupby(level=0).rolling(window=window, min_periods=window//2).mean()
    
    # Get latest ADR for each symbol
    latest_adr = adr.groupby(level=0).tail(1).droplevel('date')
    
    return latest_adr


def rolling_return(series: pd.Series, periods: int) -> float:
    """
    Calculate total return over N periods.
    
    Args:
        series: Price series
        periods: Number of periods
        
    Returns:
        Total return as decimal (e.g., 0.25 for 25%)
    """
    if len(series) < periods + 1:
        return np.nan
    
    start_price = series.iloc[-periods-1]
    end_price = series.iloc[-1]
    
    return (end_price - start_price) / start_price


def rs_score(daily_df: pd.DataFrame, periods: List[int] = [21, 63, 126]) -> pd.Series:
    """
    Calculate Relative Strength score as percentile blend of returns.
    
    Args:
        daily_df: DataFrame with MultiIndex [symbol, date] and OHLCV columns
        periods: List of periods for return calculation (1, 3, 6 months)
        
    Returns:
        Series with RS score (0-1) per symbol
    """
    # Calculate returns for each period
    returns = {}
    for period in periods:
        period_returns = daily_df['close'].groupby(level=0).apply(
            lambda x: rolling_return(x, period)
        )
        returns[f'{period}d'] = period_returns
    
    # Combine returns into DataFrame
    rs_df = pd.DataFrame(returns)
    
    # Calculate percentiles for each period
    percentiles = {}
    for period in periods:
        col = f'{period}d'
        percentiles[col] = rs_df[col].rank(pct=True)
    
    # Blend percentiles (equal weight)
    rs_score = pd.concat(percentiles.values(), axis=1).mean(axis=1)
    
    return rs_score


def detect_explosive_leg(daily_df: pd.DataFrame, window: int = 30, thresh: float = 0.25) -> pd.Series:
    """
    Detect explosive legs (≥25% impulse from swing low to swing high) within last N days.
    
    Args:
        daily_df: DataFrame with MultiIndex [symbol, date] and OHLCV columns
        window: Lookback window in days
        thresh: Minimum percentage threshold (0.25 = 25%)
        
    Returns:
        Series with boolean values per symbol
    """
    def _has_explosive_leg(symbol_data):
        if len(symbol_data) < window:
            return False
        
        # Get last N days
        recent_data = symbol_data.tail(window)
        
        # Find swing low and swing high
        swing_low = recent_data['low'].min()
        swing_high = recent_data['high'].max()
        
        # Calculate impulse percentage
        impulse_pct = (swing_high - swing_low) / swing_low
        
        return impulse_pct >= thresh
    
    explosive_legs = daily_df.groupby(level=0).apply(_has_explosive_leg)
    return explosive_legs


def detect_flag_tightening(
    daily_df: pd.DataFrame, 
    lookback_min: int = 5, 
    lookback_max: int = 20, 
    atr_contract: float = 0.7, 
    require_higher_lows: bool = True
) -> pd.Series:
    """
    Detect tight flag consolidation patterns.
    
    Args:
        daily_df: DataFrame with MultiIndex [symbol, date] and OHLCV columns
        lookback_min: Minimum days for flag formation
        lookback_max: Maximum days for flag formation
        atr_contract: ATR contraction ratio threshold
        require_higher_lows: Require at least 2 higher swing lows
        
    Returns:
        Series with boolean values per symbol
    """
    def _has_tight_flag(symbol_data):
        if len(symbol_data) < lookback_max:
            return False
        
        # Get recent data for flag analysis
        recent_data = symbol_data.tail(lookback_max)
        
        # Calculate ATR
        high_low = recent_data['high'] - recent_data['low']
        high_close = np.abs(recent_data['high'] - recent_data['close'].shift())
        low_close = np.abs(recent_data['low'] - recent_data['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=14, min_periods=7).mean()
        
        if len(atr.dropna()) < 10:
            return False
        
        # Check ATR contraction
        recent_atr = atr.tail(lookback_min).mean()
        baseline_atr = atr.iloc[-lookback_max:-lookback_min].mean()
        
        if recent_atr > baseline_atr * atr_contract:
            return False
        
        # Check for higher lows if required
        if require_higher_lows:
            lows = recent_data['low'].tail(lookback_min)
            if len(lows) >= 3:
                # Check if we have at least 2 higher lows
                higher_lows = 0
                for i in range(1, len(lows)):
                    if lows.iloc[i] > lows.iloc[i-1]:
                        higher_lows += 1
                
                if higher_lows < 2:
                    return False
        
        return True
    
    tight_flags = daily_df.groupby(level=0).apply(_has_tight_flag)
    return tight_flags


def market_gate(
    qqq_df: pd.DataFrame, 
    ema_short: int = 10, 
    ema_long: int = 20, 
    rising_lookback: int = 3
) -> Tuple[bool, Dict]:
    """
    Evaluate market gate using QQQ EMAs.
    
    Args:
        qqq_df: DataFrame with QQQ daily data (close prices)
        ema_short: Short EMA period
        ema_long: Long EMA period
        rising_lookback: Days to check for rising EMAs
        
    Returns:
        Tuple of (gate_bool, meta_dict)
    """
    if len(qqq_df) < ema_long + rising_lookback:
        logger.warning("Insufficient data for market gate calculation")
        return False, {"error": "insufficient_data"}
    
    # Calculate EMAs
    close_prices = qqq_df['close']
    ema_10 = ema(close_prices, ema_short)
    ema_20 = ema(close_prices, ema_long)
    
    # Get latest values
    latest_ema_10 = ema_10.iloc[-1]
    latest_ema_20 = ema_20.iloc[-1]
    
    # Check if EMAs are rising over lookback period
    if len(ema_10) < rising_lookback + 1:
        return False, {"error": "insufficient_lookback_data"}
    
    ema_10_slope = (ema_10.iloc[-1] - ema_10.iloc[-rising_lookback-1]) / rising_lookback
    ema_20_slope = (ema_20.iloc[-1] - ema_20.iloc[-rising_lookback-1]) / rising_lookback
    
    # Gate conditions: both EMAs rising AND EMA10 > EMA20
    ema_10_rising = ema_10_slope > 0
    ema_20_rising = ema_20_slope > 0
    ema_10_above_20 = latest_ema_10 > latest_ema_20
    
    gate_open = ema_10_rising and ema_20_rising and ema_10_above_20
    
    meta = {
        "ema_10": latest_ema_10,
        "ema_20": latest_ema_20,
        "ema_10_slope": ema_10_slope,
        "ema_20_slope": ema_20_slope,
        "rising_lookback": rising_lookback,
        "ema_10_rising": ema_10_rising,
        "ema_20_rising": ema_20_rising,
        "ema_10_above_20": ema_10_above_20,
        "close": close_prices.iloc[-1]
    }
    
    return gate_open, meta


def calculate_atr(daily_df: pd.DataFrame, window: int = 14) -> pd.Series:
    """
    Calculate Average True Range for each symbol.
    
    Args:
        daily_df: DataFrame with MultiIndex [symbol, date] and OHLCV columns OR single symbol DataFrame
        window: ATR window
        
    Returns:
        Series with ATR per symbol, or single value for single symbol DataFrame
    """
    def _calc_atr(symbol_data):
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
        atr = true_range.rolling(window=window, min_periods=window//2).mean()
        
        return atr.iloc[-1] if not atr.empty else np.nan
    
    # Check if DataFrame has MultiIndex (multiple symbols) or single index
    if isinstance(daily_df.index, pd.MultiIndex):
        atr_values = daily_df.groupby(level=0).apply(_calc_atr)
        return atr_values
    else:
        # Single symbol DataFrame
        atr_value = _calc_atr(daily_df)
        return pd.Series([atr_value], index=['single'])


def calculate_volume_profile(daily_df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Calculate volume profile metrics for each symbol.
    
    Args:
        daily_df: DataFrame with MultiIndex [symbol, date] and OHLCV columns
        window: Rolling window for volume analysis
        
    Returns:
        Series with average volume per symbol
    """
    avg_volume = daily_df['volume'].groupby(level=0).rolling(
        window=window, min_periods=window//2
    ).mean().groupby(level=0).tail(1).droplevel(1)
    
    return avg_volume


def detect_gap(daily_df: pd.DataFrame, gap_min_pct: float = 10.0) -> pd.Series:
    """
    Detect gaps in daily data.
    
    Args:
        daily_df: DataFrame with MultiIndex [symbol, date] and OHLCV columns
        gap_min_pct: Minimum gap percentage to detect
        
    Returns:
        Series with gap percentage per symbol
    """
    def _detect_gap(symbol_data):
        if len(symbol_data) < 2:
            return 0.0
        
        prev_close = symbol_data['close'].iloc[-2]
        current_open = symbol_data['open'].iloc[-1]
        
        gap_pct = (current_open - prev_close) / prev_close * 100
        return gap_pct if gap_pct >= gap_min_pct else 0.0
    
    gaps = daily_df.groupby(level=0).apply(_detect_gap)
    return gaps


def detect_volume_spike(
    minute_df: pd.DataFrame, 
    minutes: int = 10, 
    multiplier: float = 2.0
) -> pd.Series:
    """
    Detect volume spikes in intraday data.
    
    Args:
        minute_df: DataFrame with MultiIndex [symbol, timestamp] and OHLCV columns
        minutes: Number of minutes to check for volume spike
        multiplier: Volume multiplier threshold
        
    Returns:
        Series with volume ratio per symbol
    """
    def _detect_volume_spike(symbol_data):
        if len(symbol_data) < minutes:
            return 0.0
        
        # Get early volume
        early_volume = symbol_data['volume'].head(minutes).sum()
        
        # Calculate average volume (use recent days if available)
        avg_volume = symbol_data['volume'].mean()
        
        if avg_volume > 0:
            volume_ratio = early_volume / avg_volume
            return volume_ratio if volume_ratio >= multiplier else 0.0
        
        return 0.0
    
    volume_spikes = minute_df.groupby(level=0).apply(_detect_volume_spike)
    return volume_spikes


def detect_impulse(daily_df: pd.DataFrame, window: int = 60, min_pct: float = 30.0) -> pd.Series:
    """
    Detect impulse moves (big moves within a window).
    
    Args:
        daily_df: DataFrame with MultiIndex [symbol, date] and OHLCV columns
        window: Lookback window in days
        min_pct: Minimum percentage for impulse
        
    Returns:
        Series with impulse percentage per symbol
    """
    def _detect_impulse(symbol_data):
        if len(symbol_data) < window:
            return 0.0
        
        recent_data = symbol_data.tail(window)
        
        # Find swing low and swing high
        swing_low = recent_data['low'].min()
        swing_high = recent_data['high'].max()
        
        if swing_high > swing_low:
            impulse_pct = (swing_high - swing_low) / swing_low * 100
            return impulse_pct if impulse_pct >= min_pct else 0.0
        
        return 0.0
    
    impulses = daily_df.groupby(level=0).apply(_detect_impulse)
    return impulses


def calculate_flatness_score(daily_df: pd.DataFrame, periods: List[int] = [63, 126]) -> pd.Series:
    """
    Calculate flatness score - how flat the stock has been over prior periods.
    
    Args:
        daily_df: DataFrame with MultiIndex [symbol, date] and OHLCV columns
        periods: List of periods to check (in days)
        
    Returns:
        Series with flatness score per symbol (0-1, higher = flatter)
    """
    def _calculate_flatness(symbol_data):
        if len(symbol_data) < max(periods):
            return 0.0
        
        flatness_scores = []
        
        for period in periods:
            period_data = symbol_data.tail(period)
            if len(period_data) < period:
                continue
            
            # Calculate return over period
            period_return = abs((period_data['close'].iloc[-1] - period_data['close'].iloc[0]) / period_data['close'].iloc[0])
            
            # Lower return = flatter = higher score
            flatness_score = max(0, 1 - period_return)
            flatness_scores.append(flatness_score)
        
        return sum(flatness_scores) / len(flatness_scores) if flatness_scores else 0.0
    
    flatness = daily_df.groupby(level=0).apply(_calculate_flatness)
    return flatness
