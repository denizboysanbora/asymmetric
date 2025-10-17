#!/usr/bin/env python3
"""
Momentum Scanner - Detects biggest intraday movers
Output format: $SYMBOL $PRICE +X.XX%
"""
import os
import sys
import numpy as np
import pandas as pd
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
from alpaca.data.requests import StockBarsRequest
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
        
        # Only include significant upward moves (>1%)
        if intraday_change >= 1.0:
            # Calculate technical indicators
            closes = [float(bar.close) for bar in bars]
            highs = [float(bar.high) for bar in bars]
            lows = [float(bar.low) for bar in bars]
            
            rsi = calculate_rsi(closes)
            atr = calculate_atr(highs, lows, closes)
            z_score = calculate_z_score(closes)
            
            movers.append({
                'symbol': sym,
                'price': current_price,
                'change_pct': intraday_change,
                'asset_type': 'stock',
                'rsi': rsi,
                'atr': atr,
                'z_score': z_score
            })
    
    # Sort by change percentage (biggest upward movers first)
    movers.sort(key=lambda x: x['change_pct'], reverse=True)
    
    return movers[:top_n]


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

def get_intraday_movers(top_n=10):
    """Get top N stock intraday movers"""
    return get_stock_movers(top_n)

def format_momentum_signal(symbol, price, change_pct, rsi=50, atr=1.0, z_score=0.0):
    """Format momentum signal: $SYMBOL $PRICE +X.XX% | ## RSI | X.XXx ATR | Z X.XX | Momentum"""
    # Format price: no cents for thousands+, with cents for under $1000
    price_str = f"${price:,.0f}" if price >= 1000 else f"${price:,.2f}"
    return f"${symbol} {price_str} {change_pct:+.2f}% | {rsi:.0f} RSI | {atr:.2f}x ATR | Z {z_score:.2f} | Momentum"

def main():
    """Main momentum scanner"""
    print("📈 Scanning for momentum stocks...", file=sys.stderr)
    
    try:
        movers = get_intraday_movers(top_n=10)
        
        if not movers:
            print("No significant intraday movers found", file=sys.stderr)
            return
        
        print(f"Found {len(movers)} momentum stocks", file=sys.stderr)
        
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
            signal = format_momentum_signal(
                mover['symbol'], 
                mover['price'], 
                mover['change_pct'],
                mover.get('rsi', 50),
                mover.get('atr', 1.0),
                mover.get('z_score', 0.0)
            )
            print(signal)
            
    except Exception as e:
        print(f"Momentum scan failed: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
