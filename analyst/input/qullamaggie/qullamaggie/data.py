"""
Data layer for Qullamaggie.
Handles Alpaca API interactions for fetching historical and intraday data.
"""
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass, AssetStatus
from loguru import logger


def now_et() -> datetime:
    """Get current datetime in America/New_York timezone."""
    import pytz
    et = pytz.timezone('America/New_York')
    return datetime.now(et)


def get_daily_bars(symbols: List[str], lookback_days: int = 252) -> pd.DataFrame:
    """
    Fetch daily bars for symbols using Alpaca API.
    
    Args:
        symbols: List of stock symbols
        lookback_days: Number of days to look back (default 252 for 1 year)
        
    Returns:
        DataFrame with MultiIndex [symbol, date] and columns [open, high, low, close, volume]
    """
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    if not api_key or not secret_key:
        raise ValueError("Missing Alpaca API credentials")
    
    client = StockHistoricalDataClient(api_key, secret_key)
    
    # Calculate start date
    end_date = now_et().date()
    start_date = end_date - timedelta(days=lookback_days + 30)  # Extra buffer for weekends/holidays
    
    request_params = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=TimeFrame.Day,
        start=start_date,
        end=end_date,
        adjustment='raw'
    )
    
    try:
        bars = client.get_stock_bars(request_params)
        
        # Convert to DataFrame
        data = []
        if hasattr(bars, 'data'):
            # BarSet has a data attribute
            for symbol, symbol_bars in bars.data.items():
                for bar in symbol_bars:
                    data.append({
                        'symbol': symbol,
                        'date': bar.timestamp.date(),
                        'open': float(bar.open),
                        'high': float(bar.high),
                        'low': float(bar.low),
                        'close': float(bar.close),
                        'volume': int(bar.volume)
                    })
        else:
            # Try direct iteration
            for symbol, symbol_bars in bars.items():
                for bar in symbol_bars:
                    data.append({
                        'symbol': symbol,
                        'date': bar.timestamp.date(),
                        'open': float(bar.open),
                        'high': float(bar.high),
                        'low': float(bar.low),
                        'close': float(bar.close),
                        'volume': int(bar.volume)
                    })
        
        if not data:
            logger.warning(f"No daily data found for symbols: {symbols}")
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index(['symbol', 'date']).sort_index()
        
        logger.info(f"Fetched daily data for {len(df.index.get_level_values('symbol').unique())} symbols")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching daily bars: {e}")
        raise


def get_intraday_bars(
    symbols: List[str], 
    start: datetime, 
    end: datetime, 
    timeframe: str = "1Min"
) -> pd.DataFrame:
    """
    Fetch intraday bars for symbols using Alpaca API.
    
    Args:
        symbols: List of stock symbols
        start: Start datetime
        end: End datetime
        timeframe: Bar timeframe ("1Min", "5Min", etc.)
        
    Returns:
        DataFrame with MultiIndex [symbol, timestamp] and columns [open, high, low, close, volume]
    """
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    if not api_key or not secret_key:
        raise ValueError("Missing Alpaca API credentials")
    
    client = StockHistoricalDataClient(api_key, secret_key)
    
    # Parse timeframe
    if timeframe == "1Min":
        tf = TimeFrame(1, TimeFrameUnit.Minute)
    elif timeframe == "5Min":
        tf = TimeFrame(5, TimeFrameUnit.Minute)
    else:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    
    request_params = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=tf,
        start=start,
        end=end,
        adjustment='raw'
    )
    
    try:
        bars = client.get_stock_bars(request_params)
        
        # Convert to DataFrame
        data = []
        for symbol, symbol_bars in bars.items():
            for bar in symbol_bars:
                data.append({
                    'symbol': symbol,
                    'timestamp': bar.timestamp,
                    'open': float(bar.open),
                    'high': float(bar.high),
                    'low': float(bar.low),
                    'close': float(bar.close),
                    'volume': int(bar.volume)
                })
        
        if not data:
            logger.warning(f"No intraday data found for symbols: {symbols}")
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index(['symbol', 'timestamp']).sort_index()
        
        logger.info(f"Fetched intraday data for {len(df.index.get_level_values('symbol').unique())} symbols")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching intraday bars: {e}")
        raise


def get_premarket_stats(symbols: List[str], prior_close_map: Dict[str, float]) -> pd.DataFrame:
    """
    Detect premarket gaps for symbols.
    Note: This is a placeholder implementation as extended hours data availability
    varies by Alpaca plan. In practice, this would fetch premarket bars and calculate gaps.
    
    Args:
        symbols: List of stock symbols
        prior_close_map: Dict mapping symbol to prior close price
        
    Returns:
        DataFrame with columns: symbol, gap_pct, premkt_notional, availability
    """
    # For now, return placeholder data indicating premarket unavailable
    # In a full implementation, this would fetch extended hours data
    
    data = []
    for symbol in symbols:
        data.append({
            'symbol': symbol,
            'gap_pct': 0.0,
            'premkt_notional': 0.0,
            'availability': 'premarket_unavailable'
        })
    
    df = pd.DataFrame(data)
    logger.warning("Premarket data not available with current Alpaca plan - gaps will be marked as unavailable")
    return df


def get_dynamic_universe(
    min_price: float = 10.0,
    min_avg_volume: int = 100000,
    require_options: bool = True,
    exchanges: List[str] = None
) -> List[str]:
    """
    Dynamically fetch liquid stocks from Alpaca API.
    
    Args:
        min_price: Minimum stock price
        min_avg_volume: Minimum average volume
        require_options: Require options availability
        exchanges: Allowed exchanges
        
    Returns:
        List of stock symbols
    """
    if exchanges is None:
        exchanges = ["NYSE", "NASDAQ"]
    
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    if not api_key or not secret_key:
        raise ValueError("Missing Alpaca API credentials")
    
    # Keywords to filter out ETFs and leveraged products
    etf_keywords = ['ETF', 'Trust', 'Fund', 'Index', 'REIT']
    leveraged_keywords = ['Ultra', '2x', '3x', 'Bull', 'Bear', 'Inverse', 'Short', 'Leveraged', 'ProShares', 'Direxion', 'Daily']
    
    liquid_stocks = []
    try:
        trading_client = TradingClient(api_key, secret_key, paper=True)
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
                if require_options:
                    attributes = getattr(asset, 'attributes', []) or []
                    if 'has_options' not in attributes:
                        continue
                
                # Filter out ETFs and leveraged products
                name = getattr(asset, 'name', '') or ''
                is_etf = any(keyword in name for keyword in etf_keywords)
                is_leveraged = any(keyword in name for keyword in leveraged_keywords)
                
                if not is_etf and not is_leveraged:
                    liquid_stocks.append(asset.symbol)
                    
    except Exception as e:
        logger.error(f"Could not fetch liquid stocks dynamically: {e}")
        # Fallback to a basic list
        fallback_symbols = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "NFLX", "INTC",
            "CRM", "ADBE", "PYPL", "NFLX", "CMCSA", "PEP", "COST", "AVGO", "TXN", "QCOM",
            "CHTR", "SBUX", "GILD", "FISV", "BKNG", "ISRG", "REGN", "VRTX", "ADP", "TMO"
        ]
        logger.info(f"Using fallback symbol list: {len(fallback_symbols)} stocks")
        return fallback_symbols
    
    # Always include major ETFs (exceptions to ETF exclusion rule)
    always_include = ["SPY", "QQQ", "GLD"]
    all_symbols = sorted(set(liquid_stocks + always_include))
    
    logger.info(f"Dynamic universe: {len(all_symbols)} symbols")
    return all_symbols
