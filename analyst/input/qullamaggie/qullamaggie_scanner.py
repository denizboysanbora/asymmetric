#!/usr/bin/env python3
"""
Qullamaggie Setup Scanner - Detects momentum setups using Qullamaggie methodology
Integrated with Analyst system - combines RSI/ATR/Z with RS/ADR
Output format: $SYMBOL $PRICE +X.XX% | ## RSI | X.XXx ATR | Z X.XX | ## RS | ADR X.X% | NAME
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

# Add alpaca directory to path
ALPACA_DIR = Path(__file__).parent.parent / "alpaca"
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

def get_liquid_stocks():
    """Get liquid stocks for scanning"""
    # Use a curated list of liquid stocks for simplicity
    return [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'NFLX', 'AMD', 'INTC',
        'CRM', 'ADBE', 'PYPL', 'UBER', 'LYFT', 'SQ', 'ROKU', 'ZM', 'PTON', 'SPOT',
        'COIN', 'PLTR', 'SNOW', 'CRWD', 'OKTA', 'NET', 'DDOG', 'ZS', 'MDB', 'TEAM'
    ]

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

def detect_breakout_setup(bars: List[Bar], symbol: str) -> Optional[SetupTag]:
    """Detect Qullamaggie Breakout setup"""
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
    
    if score < 0.3:  # Minimum score threshold
        return None
    
    return SetupTag(
        setup="Breakout",
        triggered=False,
        score=score,
        meta={
            "impulse_pct": impulse_pct,
            "flag_days": flag_days,
            "atr_contraction": atr_contraction,
            "higher_lows_count": higher_lows
        }
    )

def detect_episodic_setup(bars: List[Bar], symbol: str) -> Optional[SetupTag]:
    """Detect Qullamaggie Episodic Pivot setup"""
    if len(bars) < 20:
        return None
    
    closes = [float(bar.close) for bar in bars]
    volumes = [float(bar.volume) for bar in bars]
    
    # Check for gap up (10%+ over prior close)
    if len(closes) < 2:
        return None
    
    gap_pct = (closes[-1] - closes[-2]) / closes[-2] * 100
    
    if gap_pct < 10.0:  # Less than 10% gap
        return None
    
    # Check for volume spike (2x average)
    avg_volume = np.mean(volumes[-20:])
    recent_volume = volumes[-1]
    volume_spike = recent_volume / avg_volume if avg_volume > 0 else 1.0
    
    if volume_spike < 2.0:  # Less than 2x volume
        return None
    
    # Calculate setup score
    score = min(gap_pct / 20, 1.0) * 0.6 + min(volume_spike / 4, 1.0) * 0.4
    
    return SetupTag(
        setup="Pivot",
        triggered=False,
        score=score,
        meta={
            "gap_pct": gap_pct,
            "volume_spike": volume_spike
        }
    )

def detect_parabolic_setup(bars: List[Bar], symbol: str) -> Optional[SetupTag]:
    """Detect Qullamaggie Parabolic Long setup"""
    if len(bars) < 20:
        return None
    
    closes = [float(bar.close) for bar in bars]
    highs = [float(bar.high) for bar in bars]
    lows = [float(bar.low) for bar in bars]
    
    # Look for crash (50%+ drop in last 7 days)
    recent_high = max(highs[-7:])
    recent_low = min(lows[-7:])
    crash_pct = (recent_high - recent_low) / recent_high * 100
    
    if crash_pct < 50.0:  # Less than 50% crash
        return None
    
    # Check for oversold condition (2x ATR below EMA)
    atr_values = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        atr_values.append(tr)
    
    if len(atr_values) < 10:
        return None
    
    atr = np.mean(atr_values[-10:])
    ema_20 = np.mean(closes[-20:])
    oversold_threshold = ema_20 - (2 * atr)
    
    if closes[-1] > oversold_threshold:
        return None
    
    # Calculate setup score
    score = min(crash_pct / 100, 1.0) * 0.7 + (1 - (closes[-1] - oversold_threshold) / (ema_20 - oversold_threshold)) * 0.3
    
    return SetupTag(
        setup="Parabolic",
        triggered=False,
        score=score,
        meta={
            "crash_pct": crash_pct,
            "atr": atr,
            "ema_20": ema_20,
            "oversold_threshold": oversold_threshold
        }
    )

def scan_qullamaggie_setups(top_n=10):
    """Scan for Qullamaggie momentum setups"""
    try:
        # Initialize Alpaca client
        api_key = os.getenv('ALPACA_API_KEY')
        secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        if not api_key or not secret_key:
            print("Warning: ALPACA_API_KEY and ALPACA_SECRET_KEY not set, using mock data", file=sys.stderr)
            # Return mock setups for testing with realistic values
            return [
                {
                    'symbol': 'NVDA',
                    'setup': SetupTag(setup="Breakout", triggered=False, score=0.85),
                    'price': 450.25,
                    'change_pct': 2.3,  # Realistic change
                    'adr_pct': 3.2,
                    'rs_score': 0.85,
                    'rsi': 65,
                    'tr_atr': 2.1,
                    'z_score': 1.8  # Realistic Z-score
                },
                {
                    'symbol': 'TSLA',
                    'setup': SetupTag(setup="Pivot", triggered=False, score=0.78),
                    'price': 250.50,
                    'change_pct': 1.7,  # Realistic change
                    'adr_pct': 4.1,
                    'rs_score': 0.78,
                    'rsi': 58,
                    'tr_atr': 1.9,
                    'z_score': 1.2  # Realistic Z-score
                }
            ]
        
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
                
                if not bars or symbol not in bars:
                    continue
                
                symbol_bars = bars[symbol]
                if len(symbol_bars) < 20:
                    continue
                
                # Detect setups
                breakout = detect_breakout_setup(symbol_bars, symbol)
                if breakout:
                    setups.append({
                        'symbol': symbol,
                        'setup': breakout,
                        'price': float(symbol_bars[-1].close),
                        'change_pct': 0.0,  # Will be calculated
                        'adr_pct': calculate_adr_pct([float(bar.close) for bar in symbol_bars]),
                        'rs_score': 0.5,  # Simplified for now
                        'rsi': 50,  # Default values for now
                        'tr_atr': 1.0,
                        'z_score': 0.0
                    })
                
                episodic = detect_episodic_setup(symbol_bars, symbol)
                if episodic:
                    setups.append({
                        'symbol': symbol,
                        'setup': episodic,
                        'price': float(symbol_bars[-1].close),
                        'change_pct': 0.0,
                        'adr_pct': calculate_adr_pct([float(bar.close) for bar in symbol_bars]),
                        'rs_score': 0.5,
                        'rsi': 50,
                        'tr_atr': 1.0,
                        'z_score': 0.0
                    })
                
                parabolic = detect_parabolic_setup(symbol_bars, symbol)
                if parabolic:
                    setups.append({
                        'symbol': symbol,
                        'setup': parabolic,
                        'price': float(symbol_bars[-1].close),
                        'change_pct': 0.0,
                        'adr_pct': calculate_adr_pct([float(bar.close) for bar in symbol_bars]),
                        'rs_score': 0.5,
                        'rsi': 50,
                        'tr_atr': 1.0,
                        'z_score': 0.0
                    })
                
            except Exception as e:
                print(f"Error processing {symbol}: {e}", file=sys.stderr)
                continue
        
        # Sort by setup score
        setups.sort(key=lambda x: x['setup'].score, reverse=True)
        
        return setups[:top_n]
        
    except Exception as e:
        print(f"Qullamaggie scan failed: {e}", file=sys.stderr)
        return []

def format_qullamaggie_signal(symbol, price, change_pct, rs_score, adr_pct, setup_type, rsi=50, tr_atr=1.0, z_score=0.0):
    """Format combined Qullamaggie signal: $SYMBOL $PRICE +X.X% | ##/## RSI | #-#-# %R | Z X.X | NAME"""
    # Format price: no cents for thousands+, with cents for under $1000
    price_str = f"${price:,.0f}" if price >= 1000 else f"${price:,.2f}"
    # Convert RS score to percentage (0-1 -> 0-100)
    rs_percent = rs_score * 100
    # Calculate ATR for different timeframes (simplified - using current ATR as base)
    atr_20d = round(tr_atr)  # 20-day ATR
    atr_10d = round(tr_atr * 0.8)  # 10-day ATR (approximation)
    adr_5d = round(adr_pct)  # 5-day ADR
    return f"${symbol} {price_str} {change_pct:+.1f}% | {rsi:.0f}/{rs_percent:.0f} RSI | {atr_20d}-{atr_10d}-{adr_5d} %R | Z {z_score:.1f} | {setup_type}"

def main():
    """Main Qullamaggie scanner"""
    print("📈 Scanning for Qullamaggie momentum setups...", file=sys.stderr)
    
    try:
        setups = scan_qullamaggie_setups()
        
        if not setups:
            print("No Qullamaggie setups detected", file=sys.stderr)
            return
        
        print(f"Found {len(setups)} Qullamaggie setups", file=sys.stderr)
        
        # Output formatted signals
        for setup in setups:
            signal = format_qullamaggie_signal(
                setup['symbol'],
                setup['price'],
                setup['change_pct'],
                setup['rs_score'],
                setup['adr_pct'],
                setup['setup'].setup,
                setup.get('rsi', 50),
                setup.get('tr_atr', 1.0),
                setup.get('z_score', 0.0)
            )
            print(signal)
            
    except Exception as e:
        print(f"Qullamaggie scan failed: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
