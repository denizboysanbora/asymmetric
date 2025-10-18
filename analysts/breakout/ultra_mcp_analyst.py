#!/usr/bin/env python3
"""
Ultra Optimized MCP Analyst
Maximum speed and efficiency using full MCP integration and parallel processing
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

class UltraMCPAnalyst:
    """Ultra-optimized MCP analyst with maximum parallel processing"""
    
    def __init__(self):
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        if not self.api_key or not self.secret_key:
            print("❌ ALPACA_API_KEY and ALPACA_SECRET_KEY not set", file=sys.stderr)
            sys.exit(1)
        
        # Use the original Alpaca client for maximum speed
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            from alpaca.trading.client import TradingClient
            from alpaca.trading.requests import MarketOrderRequest
            from alpaca.trading.enums import OrderSide, TimeInForce
            
            self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)
            self.trading_client = TradingClient(self.api_key, self.secret_key)
            self.StockBarsRequest = StockBarsRequest
            self.TimeFrame = TimeFrame
            self.MarketOrderRequest = MarketOrderRequest
            self.OrderSide = OrderSide
            self.TimeInForce = TimeInForce
            print("✅ Ultra-fast Alpaca clients initialized", file=sys.stderr)
        except Exception as e:
            print(f"❌ Failed to initialize Alpaca clients: {e}", file=sys.stderr)
            sys.exit(1)
    
    def get_ultra_liquid_stocks(self) -> List[str]:
        """Get dynamic liquid stocks from original breakout analysis"""
        try:
            # Import the original get_liquid_stocks function
            from breakout_analysis import get_liquid_stocks as original_get_liquid_stocks
            return original_get_liquid_stocks()
        except Exception as e:
            print(f"⚠️  Could not load dynamic universe: {e}", file=sys.stderr)
            print("📊 Using minimal fallback list...", file=sys.stderr)
            # Minimal fallback - just the most essential stocks
            return [
                'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'AMD', 'INTC',
                'SPY', 'QQQ', 'IWM', 'XLF', 'XLK', 'XLE', 'XLV', 'XLI', 'XLY', 'XLP'
            ]
    
    async def get_stock_bars_ultra(self, symbols: List[str]) -> Dict[str, List]:
        """Get stock bars for multiple symbols in one request for maximum efficiency"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            
            # Request bars for all symbols at once
            request = self.StockBarsRequest(
                symbol_or_symbols=symbols,
                timeframe=self.TimeFrame.Day,
                start=start_date,
                end=end_date
            )
            
            bars = self.data_client.get_stock_bars(request)
            
            if bars and bars.data:
                return {symbol: symbol_bars for symbol, symbol_bars in bars.data.items() if len(symbol_bars) >= 30}
            else:
                return {}
                
        except Exception as e:
            print(f"⚠️  Error getting bars: {e}", file=sys.stderr)
            return {}
    
    async def analyze_stocks_batch(self, symbols: List[str]) -> List[Dict]:
        """Analyze multiple stocks in parallel for maximum speed"""
        # Get all bars at once
        all_bars = await self.get_stock_bars_ultra(symbols)
        
        setups = []
        
        # Process each stock
        for symbol in symbols:
            try:
                if symbol not in all_bars:
                    continue
                
                bars = all_bars[symbol]
                
                # Calculate technical indicators
                closes = [float(bar.close) for bar in bars]
                highs = [float(bar.high) for bar in bars]
                lows = [float(bar.low) for bar in bars]
                
                rsi = calculate_rsi(closes)
                atr = calculate_atr(highs, lows, closes)
                z_score = calculate_z_score(closes)
                adr_pct = calculate_adr_pct(closes)
                
                # Calculate change percentage
                if len(closes) >= 2:
                    change_pct = ((closes[-1] - closes[-2]) / closes[-2]) * 100
                else:
                    change_pct = 0.0
                
                # Detect breakouts
                flag_breakout = detect_flag_breakout_setup(bars, symbol)
                range_breakout = detect_range_breakout_setup(bars, symbol)
                
                # Return the best breakout signal
                if flag_breakout and range_breakout:
                    if flag_breakout.score >= range_breakout.score:
                        setup = flag_breakout
                    else:
                        setup = range_breakout
                elif flag_breakout:
                    setup = flag_breakout
                elif range_breakout:
                    setup = range_breakout
                else:
                    continue
                
                setups.append({
                    'symbol': symbol,
                    'setup': setup,
                    'price': float(bars[-1].close),
                    'change_pct': change_pct,
                    'adr_pct': adr_pct,
                    'rsi': rsi,
                    'tr_atr': atr,
                    'z_score': z_score,
                    'bars': bars
                })
                
            except Exception as e:
                print(f"Error analyzing {symbol}: {e}", file=sys.stderr)
                continue
        
        return setups
    
    async def get_market_status_ultra(self) -> bool:
        """Get market status quickly"""
        try:
            clock = self.trading_client.get_clock()
            return clock.is_open
        except Exception as e:
            print(f"⚠️  Could not get market status: {e}", file=sys.stderr)
            return False
    
    async def get_account_info_ultra(self) -> Dict:
        """Get account info quickly"""
        try:
            account = self.trading_client.get_account()
            return {
                'buying_power': float(account.buying_power),
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value)
            }
        except Exception as e:
            print(f"⚠️  Could not get account info: {e}", file=sys.stderr)
            return {'buying_power': 0, 'cash': 0, 'portfolio_value': 0}
    
    async def scan_universe_ultra(self, max_stocks: int = 0) -> List[Dict]:
        """Ultra-fast universe scan with maximum parallelization"""
        print("🚀 Ultra MCP Analyst - Maximum Speed Scan", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        
        # Get market status
        market_open = await self.get_market_status_ultra()
        print(f"📅 Market Status: {'Open' if market_open else 'Closed'}", file=sys.stderr)
        
        # Get account info
        account_info = await self.get_account_info_ultra()
        buying_power = account_info.get('buying_power', 0)
        print(f"💰 Buying Power: ${buying_power:,.2f}", file=sys.stderr)
        
        # Get liquid stocks
        all_symbols = self.get_ultra_liquid_stocks()
        symbols = all_symbols[:max_stocks] if max_stocks > 0 else all_symbols
        print(f"📊 Analyzing {len(symbols)} ultra-liquid stocks...", file=sys.stderr)
        
        # Process in large batches for maximum efficiency
        batch_size = 50  # Process 50 stocks at a time
        all_setups = []
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            print(f"📈 Processing mega-batch {i//batch_size + 1}/{(len(symbols)-1)//batch_size + 1} ({len(batch)} stocks)...", file=sys.stderr)
            
            # Analyze entire batch
            batch_setups = await self.analyze_stocks_batch(batch)
            all_setups.extend(batch_setups)
        
        # Sort by setup score
        def sort_key(x):
            base_score = x['setup'].score
            if x['setup'].setup == "Flag Breakout":
                return base_score + 0.1
            return base_score
        
        all_setups.sort(key=sort_key, reverse=True)
        
        print(f"🎯 Found {len(all_setups)} breakout signals", file=sys.stderr)
        
        return all_setups
    
    async def place_trade_ultra(self, symbol: str, side: str, quantity: int) -> Dict:
        """Place trade with ultra-fast execution"""
        try:
            market_order_data = self.MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=self.OrderSide.BUY if side == "buy" else self.OrderSide.SELL,
                time_in_force=self.TimeInForce.DAY
            )
            
            order = self.trading_client.submit_order(order_data=market_order_data)
            
            return {
                'id': order.id,
                'symbol': order.symbol,
                'qty': order.qty,
                'side': order.side.value,
                'status': order.status.value
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def execute_trade_ultra(self, signal: Dict) -> bool:
        """Execute trade with ultra-fast execution"""
        try:
            symbol = signal['symbol']
            price = signal['price']
            
            # Get account info
            account_info = await self.get_account_info_ultra()
            buying_power = account_info.get('buying_power', 0)
            
            if buying_power < 1000:
                print(f"💰 Insufficient buying power: ${buying_power:,.2f}", file=sys.stderr)
                return False
            
            # Calculate position size (2% of buying power for ultra-conservative)
            position_value = buying_power * 0.02
            quantity = int(position_value / price)
            
            if quantity < 1:
                print(f"📊 Position size too small for {symbol}: {quantity} shares", file=sys.stderr)
                return False
            
            # Place trade
            trade_result = await self.place_trade_ultra(symbol, "buy", quantity)
            
            if 'error' in trade_result:
                print(f"❌ Trade failed for {symbol}: {trade_result['error']}", file=sys.stderr)
                return False
            
            print(f"✅ Placed {quantity} shares of {symbol} at ${price:.2f}", file=sys.stderr)
            print(f"   Order ID: {trade_result.get('id', 'Unknown')}", file=sys.stderr)
            print(f"   Position Value: ${position_value:,.2f}", file=sys.stderr)
            return True
            
        except Exception as e:
            print(f"❌ Error executing trade for {symbol}: {e}", file=sys.stderr)
            return False

async def main():
    """Main ultra-optimized function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ultra Optimized MCP Analyst')
    parser.add_argument('--auto-trade', action='store_true', 
                       help='Enable automatic trading (default: False)')
    parser.add_argument('--max-stocks', type=int, default=0,
                       help='Maximum number of stocks to analyze (default: 0 = all)')
    parser.add_argument('--top-n', type=int, default=10,
                       help='Number of top signals to show (default: 10)')
    
    args = parser.parse_args()
    
    analyst = UltraMCPAnalyst()
    
    try:
        # Run ultra scan
        signals = await analyst.scan_universe_ultra(max_stocks=args.max_stocks)
        
        # Show top signals
        top_signals = signals[:args.top_n]
        
        # Output signals
        for signal in top_signals:
            symbol = signal['symbol']
            price = signal['price']
            change_pct = signal['change_pct']
            setup = signal['setup']
            rsi = signal['rsi']
            tr_atr = signal['tr_atr']
            z_score = signal['z_score']
            
            signal_str = format_breakout_signal(
                symbol, price, change_pct, 0.5, 0.0, setup.setup, rsi, tr_atr, z_score
            )
            print(signal_str)
        
        # Execute trades if enabled
        if args.auto_trade and signals:
            print("\n🤖 Ultra auto-trading enabled...", file=sys.stderr)
            
            # Only trade the top signal
            top_signal = signals[0]
            if top_signal['setup'].score >= 0.8:  # Ultra-high confidence
                success = await analyst.execute_trade_ultra(top_signal)
                if success:
                    print(f"✅ Ultra trade executed for {top_signal['symbol']}", file=sys.stderr)
                else:
                    print(f"❌ Ultra trade failed for {top_signal['symbol']}", file=sys.stderr)
            else:
                print("ℹ️  No ultra-high confidence signals for trading", file=sys.stderr)
        
        if not signals:
            print("No breakout signals found", file=sys.stderr)
    
    except Exception as e:
        print(f"❌ Ultra analysis failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
