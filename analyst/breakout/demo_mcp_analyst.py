#!/usr/bin/env python3
"""
Demo MCP Analyst - Shows breakout signals for demonstration
"""
import os
import sys
import numpy as np
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# Load environment variables first
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).parent.parent / "config" / "api_keys.env"
    if env_file.exists():
        load_dotenv(env_file)
        print("🔑 Loaded API keys from .env file", file=sys.stderr)
except ImportError:
    pass

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from breakout_scanner import (
    detect_flag_breakout_setup, 
    detect_range_breakout_setup, 
    calculate_rsi, 
    calculate_atr, 
    calculate_z_score,
    calculate_adr_pct,
    format_breakout_signal,
    SetupTag
)

class DemoMCPAnalyst:
    """Demo MCP analyst showing breakout signals"""
    
    def __init__(self):
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        if not self.api_key or not self.secret_key:
            print("❌ ALPACA_API_KEY and ALPACA_SECRET_KEY not set", file=sys.stderr)
            sys.exit(1)
        
        # Use the original Alpaca client
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            from alpaca.trading.client import TradingClient
            
            self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)
            self.trading_client = TradingClient(self.api_key, self.secret_key)
            self.StockBarsRequest = StockBarsRequest
            self.TimeFrame = TimeFrame
            print("✅ Demo Alpaca clients initialized", file=sys.stderr)
        except Exception as e:
            print(f"❌ Failed to initialize Alpaca clients: {e}", file=sys.stderr)
            sys.exit(1)
    
    def get_demo_stocks(self) -> List[str]:
        """Get demo stocks for demonstration"""
        return [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'AMD', 'INTC',
            'SPY', 'QQQ', 'IWM', 'XLF', 'XLK', 'XLE', 'XLV', 'XLI', 'XLY', 'XLP',
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP', 'BLK', 'SCHW', 'COF'
        ]
    
    def create_demo_signals(self) -> List[Dict]:
        """Create realistic demo signals for demonstration"""
        import random
        
        demo_stocks = self.get_demo_stocks()
        signals = []
        
        # Create some realistic demo signals
        demo_data = [
            ('AAPL', 185.50, 2.3, 65, 1.45, 1.2, 'Flag Breakout', 0.85),
            ('NVDA', 450.25, 4.1, 72, 2.1, 1.8, 'Range Breakout', 0.92),
            ('TSLA', 250.75, 3.2, 58, 1.8, 1.5, 'Flag Breakout', 0.78),
            ('MSFT', 420.30, 1.9, 68, 1.3, 1.1, 'Range Breakout', 0.73),
            ('GOOGL', 145.80, 2.7, 62, 1.6, 1.3, 'Flag Breakout', 0.81),
            ('AMZN', 155.20, 3.5, 70, 1.9, 1.6, 'Range Breakout', 0.88),
            ('META', 380.45, 2.1, 66, 1.4, 1.2, 'Flag Breakout', 0.76),
            ('AMD', 125.60, 4.3, 75, 2.2, 1.9, 'Range Breakout', 0.90),
            ('SPY', 450.15, 1.8, 61, 1.2, 1.0, 'Flag Breakout', 0.71),
            ('QQQ', 380.25, 2.4, 67, 1.5, 1.3, 'Range Breakout', 0.79)
        ]
        
        for symbol, price, change_pct, rsi, atr, z_score, setup_type, score in demo_data:
            signals.append({
                'symbol': symbol,
                'price': price,
                'change_pct': change_pct,
                'rsi': rsi,
                'tr_atr': atr,
                'z_score': z_score,
                'setup_type': setup_type,
                'score': score
            })
        
        return signals
    
    async def get_market_status(self) -> bool:
        """Get market status"""
        try:
            clock = self.trading_client.get_clock()
            return clock.is_open
        except Exception as e:
            print(f"⚠️  Could not get market status: {e}", file=sys.stderr)
            return False
    
    async def get_account_info(self) -> Dict:
        """Get account info"""
        try:
            account = self.trading_client.get_account()
            return {
                'buying_power': float(account.buying_power),
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value)
            }
        except Exception as e:
            print(f"⚠️  Could not get account info: {e}", file=sys.stderr)
            return {'buying_power': 200000, 'cash': 200000, 'portfolio_value': 200000}

async def main():
    """Main demo function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Demo MCP Analyst')
    parser.add_argument('--top-n', type=int, default=10,
                       help='Number of top signals to show (default: 10)')
    
    args = parser.parse_args()
    
    analyst = DemoMCPAnalyst()
    
    try:
        print("🚀 Demo MCP Analyst - Breakout Signal Demonstration", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        
        # Get market status
        market_open = await analyst.get_market_status()
        print(f"📅 Market Status: {'Open' if market_open else 'Closed'}", file=sys.stderr)
        
        # Get account info
        account_info = await analyst.get_account_info()
        buying_power = account_info.get('buying_power', 0)
        print(f"💰 Buying Power: ${buying_power:,.2f}", file=sys.stderr)
        
        # Get demo signals
        signals = analyst.create_demo_signals()
        print(f"📊 Generated {len(signals)} demo breakout signals", file=sys.stderr)
        
        # Sort by score
        signals.sort(key=lambda x: x['score'], reverse=True)
        
        # Show top signals
        top_signals = signals[:args.top_n]
        print(f"🎯 Showing top {len(top_signals)} signals:", file=sys.stderr)
        print("", file=sys.stderr)
        
        # Output signals
        for signal in top_signals:
            symbol = signal['symbol']
            price = signal['price']
            change_pct = signal['change_pct']
            setup_type = signal['setup_type']
            rsi = signal['rsi']
            tr_atr = signal['tr_atr']
            z_score = signal['z_score']
            
            signal_str = format_breakout_signal(
                symbol, price, change_pct, rsi, tr_atr, setup_type
            )
            print(signal_str)
        
        print("", file=sys.stderr)
        print("📊 Demo Analysis Complete!", file=sys.stderr)
        print("💡 These are demonstration signals showing the format and scoring system", file=sys.stderr)
        print("🚀 Run during market hours for real breakout detection", file=sys.stderr)
    
    except Exception as e:
        print(f"❌ Demo analysis failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
