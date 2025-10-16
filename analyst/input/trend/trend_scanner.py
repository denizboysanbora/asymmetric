#!/usr/bin/env python3
"""
Trend Scanner - Detects biggest intraday movers
Output format: $SYMBOL $PRICE +X.XX%
"""
import os
import sys
import numpy as np
from datetime import datetime, timedelta
import json
from pathlib import Path

# Add alpaca directory to path
ALPACA_DIR = Path(__file__).parent.parent / "alpaca"
sys.path.insert(0, str(ALPACA_DIR))

# Import Alpaca modules
sys.path.insert(0, str(ALPACA_DIR))
from dotenv import load_dotenv
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.historical.crypto import CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient

load_dotenv(str(ALPACA_DIR / ".env"))

def get_liquid_stocks():
    """Get list of liquid stocks for scanning"""
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
        # Fallback to major stocks
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "NFLX", "INTC", "SPY", "QQQ", "GLD"]
    
    return sorted(set(liquid_stocks))

def get_major_cryptos():
    """Get list of major cryptocurrencies for scanning"""
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

def get_stock_movers(top_n=5):
    """Get top N stock intraday movers"""
    stock_client = StockHistoricalDataClient(os.getenv('ALPACA_API_KEY'), os.getenv('ALPACA_SECRET_KEY'))
    now = datetime.now()
    
    # Get liquid stocks
    stock_symbols = get_liquid_stocks()
    print(f"Scanning {len(stock_symbols)} stocks for intraday movers...", file=sys.stderr)
    
    # Fetch today's bars (1-minute resolution for intraday)
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    request = StockBarsRequest(
        symbol_or_symbols=stock_symbols, 
        timeframe=TimeFrame(1, TimeFrameUnit.Minute), 
        start=start_today, 
        end=now
    )
    bars_dict = stock_client.get_stock_bars(request).data
    
    movers = []
    for sym in stock_symbols:
        bars = bars_dict.get(sym, [])
        if len(bars) < 2:  # Need at least 2 bars
            continue
        
        # Get today's open and current price
        today_open = float(bars[0].open)
        current_price = float(bars[-1].close)
        
        # Calculate intraday change
        intraday_change = ((current_price - today_open) / today_open) * 100.0
        
        # Only include significant moves (>1%)
        if abs(intraday_change) >= 1.0:
            movers.append({
                'symbol': sym,
                'price': current_price,
                'change_pct': intraday_change,
                'asset_type': 'stock'
            })
    
    # Sort by absolute change (biggest movers first)
    movers.sort(key=lambda x: abs(x['change_pct']), reverse=True)
    
    return movers[:top_n]

def get_crypto_movers(top_n=5):
    """Get top N crypto intraday movers"""
    crypto_client = CryptoHistoricalDataClient(os.getenv('ALPACA_API_KEY'), os.getenv('ALPACA_SECRET_KEY'))
    now = datetime.now()
    
    # Get major cryptos
    crypto_symbols = get_major_cryptos()
    print(f"Scanning {len(crypto_symbols)} cryptos for intraday movers...", file=sys.stderr)
    
    # Fetch today's bars (1-minute resolution for intraday)
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    request = CryptoBarsRequest(
        symbol_or_symbols=crypto_symbols, 
        timeframe=TimeFrame(1, TimeFrameUnit.Minute), 
        start=start_today, 
        end=now
    )
    bars_dict = crypto_client.get_crypto_bars(request).data
    
    movers = []
    for sym in crypto_symbols:
        bars = bars_dict.get(sym, [])
        if len(bars) < 2:  # Need at least 2 bars
            continue
        
        # Get today's open and current price
        today_open = float(bars[0].open)
        current_price = float(bars[-1].close)
        
        # Calculate intraday change
        intraday_change = ((current_price - today_open) / today_open) * 100.0
        
        # Only include significant moves (>1%)
        if abs(intraday_change) >= 1.0:
            # Extract base symbol (BTC from BTC/USD)
            base_symbol = sym.split('/')[0]
            movers.append({
                'symbol': base_symbol,
                'price': current_price,
                'change_pct': intraday_change,
                'asset_type': 'crypto'
            })
    
    # Sort by absolute change (biggest movers first)
    movers.sort(key=lambda x: abs(x['change_pct']), reverse=True)
    
    return movers[:top_n]

def get_intraday_movers(top_n=10):
    """Get top N intraday movers from both stocks and crypto"""
    stock_movers = get_stock_movers(top_n // 2)
    crypto_movers = get_crypto_movers(top_n // 2)
    
    # Combine and sort all movers
    all_movers = stock_movers + crypto_movers
    all_movers.sort(key=lambda x: abs(x['change_pct']), reverse=True)
    
    return all_movers[:top_n]

def format_trend_signal(symbol, price, change_pct):
    """Format trend signal: $SYMBOL $PRICE +X.XX%"""
    # Format price: no cents for thousands+, with cents for under $1000
    price_str = f"${price:,.0f}" if price >= 1000 else f"${price:,.2f}"
    return f"${symbol} {price_str} {change_pct:+.2f}%"

def main():
    """Main trend scanner"""
    print("📈 Scanning for trending stocks...", file=sys.stderr)
    
    try:
        movers = get_intraday_movers(top_n=10)
        
        if not movers:
            print("No significant intraday movers found", file=sys.stderr)
            return
        
        print(f"Found {len(movers)} trending stocks", file=sys.stderr)
        
        # Persist asset classifications for orchestrator use
        state_dir = Path(__file__).parent / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_path = state_dir / "last_trends.json"
        try:
            state_payload = [{
                "symbol": item["symbol"],
                "asset_type": item.get("asset_type", "stock")
            } for item in movers]
            state_path.write_text(json.dumps(state_payload, indent=2))
        except Exception as e:
            print(f"Warning: could not write trend state: {e}", file=sys.stderr)
        
        # Output formatted signals
        for mover in movers:
            signal = format_trend_signal(
                mover['symbol'], 
                mover['price'], 
                mover['change_pct']
            )
            print(signal)
            
    except Exception as e:
        print(f"Trend scan failed: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
