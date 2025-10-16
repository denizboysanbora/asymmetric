"""
Opening range analysis for Qullamaggie.
Computes ORH/ORL and entry triggers for momentum candidates.
"""
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional
import pandas as pd
from loguru import logger

from .data import now_et


def compute_opening_range(
    minute_df: pd.DataFrame, 
    or_minutes: int = 5,
    market_open_time: time = time(9, 30)
) -> Dict[str, Dict]:
    """
    Compute opening range high/low for each symbol.
    
    Args:
        minute_df: DataFrame with MultiIndex [symbol, timestamp] and OHLCV columns
        or_minutes: Opening range duration in minutes (default 5)
        market_open_time: Market open time (default 9:30 AM)
        
    Returns:
        Dict mapping symbol to {orh, orl, last_price, entry_triggered}
    """
    if minute_df.empty:
        logger.warning("No minute data provided for opening range calculation")
        return {}
    
    results = {}
    symbols = minute_df.index.get_level_values('symbol').unique()
    
    logger.info(f"Computing opening range for {len(symbols)} symbols")
    
    for symbol in symbols:
        try:
            symbol_data = minute_df.xs(symbol, level='symbol')
            
            if symbol_data.empty:
                logger.warning(f"No data for symbol {symbol}")
                continue
            
            # Filter for opening range period (9:30 - 9:35 ET by default)
            or_end_time = (datetime.combine(datetime.today(), market_open_time) + 
                          timedelta(minutes=or_minutes)).time()
            
            # Create time-based mask
            symbol_data = symbol_data.copy()
            symbol_data['time'] = symbol_data.index.time
            or_mask = (symbol_data['time'] >= market_open_time) & (symbol_data['time'] <= or_end_time)
            or_data = symbol_data[or_mask]
            
            if or_data.empty:
                logger.warning(f"No opening range data for {symbol} (9:30-{or_end_time.strftime('%H:%M')})")
                results[symbol] = {
                    'orh': None,
                    'orl': None,
                    'last_price': None,
                    'entry_triggered': False,
                    'error': 'no_opening_range_data'
                }
                continue
            
            # Calculate ORH and ORL
            orh = or_data['high'].max()
            orl = or_data['low'].min()
            
            # Get last available price
            last_price = symbol_data['close'].iloc[-1]
            
            # Check if entry is triggered (last price > ORH)
            entry_triggered = last_price > orh if orh is not None else False
            
            # Validate time window
            actual_start = or_data.index.min().time()
            actual_end = or_data.index.max().time()
            
            if actual_start > market_open_time:
                logger.warning(f"{symbol}: Opening range started late ({actual_start})")
            
            if actual_end < or_end_time:
                logger.warning(f"{symbol}: Opening range ended early ({actual_end})")
            
            results[symbol] = {
                'orh': float(orh),
                'orl': float(orl),
                'last_price': float(last_price),
                'entry_triggered': entry_triggered,
                'or_start': actual_start.strftime('%H:%M'),
                'or_end': actual_end.strftime('%H:%M'),
                'or_bars': len(or_data)
            }
            
            logger.debug(f"{symbol}: ORH={orh:.2f}, ORL={orl:.2f}, Last={last_price:.2f}, Triggered={entry_triggered}")
            
        except Exception as e:
            logger.error(f"Error computing opening range for {symbol}: {e}")
            results[symbol] = {
                'orh': None,
                'orl': None,
                'last_price': None,
                'entry_triggered': False,
                'error': str(e)
            }
    
    triggered_count = sum(1 for r in results.values() if r.get('entry_triggered', False))
    logger.info(f"Opening range computed for {len(results)} symbols, {triggered_count} triggered")
    
    return results


def validate_opening_range_data(
    minute_df: pd.DataFrame,
    or_minutes: int = 5,
    market_open_time: time = time(9, 30)
) -> Dict[str, bool]:
    """
    Validate that opening range data is available and complete.
    
    Args:
        minute_df: DataFrame with MultiIndex [symbol, timestamp] and OHLCV columns
        or_minutes: Opening range duration in minutes
        market_open_time: Market open time
        
    Returns:
        Dict mapping symbol to validation status
    """
    validation_results = {}
    symbols = minute_df.index.get_level_values('symbol').unique()
    
    or_end_time = (datetime.combine(datetime.today(), market_open_time) + 
                  timedelta(minutes=or_minutes)).time()
    
    for symbol in symbols:
        try:
            symbol_data = minute_df.xs(symbol, level='symbol')
            
            if symbol_data.empty:
                validation_results[symbol] = False
                continue
            
            # Check time coverage
            symbol_data = symbol_data.copy()
            symbol_data['time'] = symbol_data.index.time
            or_mask = (symbol_data['time'] >= market_open_time) & (symbol_data['time'] <= or_end_time)
            or_data = symbol_data[or_mask]
            
            # Validation criteria
            has_data = not or_data.empty
            has_minimum_bars = len(or_data) >= max(1, or_minutes // 2)  # At least half the expected bars
            
            # Check time coverage (convert time to datetime for comparison)
            or_start_dt = datetime.combine(datetime.today(), or_data.index.min().time())
            or_end_dt = datetime.combine(datetime.today(), or_data.index.max().time())
            market_open_dt = datetime.combine(datetime.today(), market_open_time)
            or_end_dt_target = datetime.combine(datetime.today(), or_end_time)
            
            covers_timeframe = (or_start_dt <= market_open_dt + timedelta(minutes=1) and
                              or_end_dt >= or_end_dt_target - timedelta(minutes=1))
            
            is_valid = has_data and has_minimum_bars and covers_timeframe
            validation_results[symbol] = is_valid
            
            if not is_valid:
                logger.debug(f"Opening range validation failed for {symbol}: "
                           f"has_data={has_data}, bars={len(or_data)}, covers_timeframe={covers_timeframe}")
            
        except Exception as e:
            logger.error(f"Error validating opening range for {symbol}: {e}")
            validation_results[symbol] = False
    
    valid_count = sum(validation_results.values())
    logger.info(f"Opening range validation: {valid_count}/{len(symbols)} symbols have valid data")
    
    return validation_results


def get_entry_signals(opening_range_results: Dict[str, Dict]) -> List[str]:
    """
    Get list of symbols with triggered entry signals.
    
    Args:
        opening_range_results: Results from compute_opening_range()
        
    Returns:
        List of symbols with entry_triggered=True
    """
    triggered_symbols = []
    
    for symbol, result in opening_range_results.items():
        if result.get('entry_triggered', False):
            triggered_symbols.append(symbol)
    
    return triggered_symbols


def calculate_or_breakout_strength(
    opening_range_results: Dict[str, Dict]
) -> Dict[str, float]:
    """
    Calculate opening range breakout strength as percentage above ORH.
    
    Args:
        opening_range_results: Results from compute_opening_range()
        
    Returns:
        Dict mapping symbol to breakout strength percentage
    """
    breakout_strength = {}
    
    for symbol, result in opening_range_results.items():
        if result.get('entry_triggered', False):
            orh = result.get('orh')
            last_price = result.get('last_price')
            
            if orh and last_price and orh > 0:
                strength = ((last_price - orh) / orh) * 100
                breakout_strength[symbol] = strength
            else:
                breakout_strength[symbol] = 0.0
        else:
            breakout_strength[symbol] = 0.0
    
    return breakout_strength


def summarize_opening_range_results(opening_range_results: Dict[str, Dict]) -> Dict:
    """
    Generate summary statistics for opening range results.
    
    Args:
        opening_range_results: Results from compute_opening_range()
        
    Returns:
        Dictionary with summary statistics
    """
    if not opening_range_results:
        return {
            "total_symbols": 0,
            "triggered_count": 0,
            "triggered_percentage": 0,
            "avg_orh": 0,
            "avg_orl": 0,
            "avg_last_price": 0
        }
    
    triggered_symbols = get_entry_signals(opening_range_results)
    triggered_count = len(triggered_symbols)
    
    # Calculate averages (excluding None values)
    orh_values = [r['orh'] for r in opening_range_results.values() if r['orh'] is not None]
    orl_values = [r['orl'] for r in opening_range_results.values() if r['orl'] is not None]
    last_prices = [r['last_price'] for r in opening_range_results.values() if r['last_price'] is not None]
    
    avg_orh = sum(orh_values) / len(orh_values) if orh_values else 0
    avg_orl = sum(orl_values) / len(orl_values) if orl_values else 0
    avg_last_price = sum(last_prices) / len(last_prices) if last_prices else 0
    
    return {
        "total_symbols": len(opening_range_results),
        "triggered_count": triggered_count,
        "triggered_percentage": (triggered_count / len(opening_range_results)) * 100,
        "avg_orh": avg_orh,
        "avg_orl": avg_orl,
        "avg_last_price": avg_last_price,
        "triggered_symbols": triggered_symbols
    }
