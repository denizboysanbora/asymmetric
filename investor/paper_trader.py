#!/usr/bin/env python3
"""
Paper Trading Investment Module
Executes paper trades based on breakout signals using Alpaca API
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import re

# Add alpaca directory to path
ALPACA_DIR = Path(__file__).parent.parent / "input" / "alpaca"
sys.path.insert(0, str(ALPACA_DIR))

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
except ImportError as e:
    print(f"Error importing Alpaca modules: {e}", file=sys.stderr)
    sys.exit(1)

class PaperTrader:
    """Paper trading implementation using Alpaca API"""
    
    def __init__(self):
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        
        if not self.api_key or not self.secret_key:
            print("Error: ALPACA_API_KEY and ALPACA_SECRET_KEY not set", file=sys.stderr)
            sys.exit(1)
        
        # Initialize Alpaca clients
        self.trading_client = TradingClient(self.api_key, self.secret_key, paper=True)
        self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)
        
        # Portfolio state
        self.state_file = Path(__file__).parent / "portfolio_state.json"
        self.portfolio = self.load_portfolio_state()
        
        # Trading parameters
        self.max_position_size = 0.1  # 10% of portfolio per position
        self.stop_loss_pct = 0.05     # 5% stop loss
        self.take_profit_pct = 0.15   # 15% take profit
    
    def load_portfolio_state(self) -> Dict:
        """Load portfolio state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default portfolio state
        return {
            "cash": 100000.0,  # Starting with $100k
            "positions": {},
            "orders": [],
            "total_value": 100000.0,
            "last_updated": datetime.now().isoformat()
        }
    
    def save_portfolio_state(self):
        """Save portfolio state to file"""
        self.portfolio["last_updated"] = datetime.now().isoformat()
        with open(self.state_file, 'w') as f:
            json.dump(self.portfolio, f, indent=2)
    
    def get_account_info(self) -> Dict:
        """Get current account information"""
        try:
            account = self.trading_client.get_account()
            return {
                "cash": float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "buying_power": float(account.buying_power),
                "equity": float(account.equity)
            }
        except Exception as e:
            print(f"Error getting account info: {e}", file=sys.stderr)
            return self.portfolio
    
    def parse_breakout_signal(self, signal_text: str) -> Optional[Dict]:
        """Parse breakout signal format: $SYMBOL $PRICE +X.X% | ## RSI | X.XXx ATR | Z X.X | Breakout"""
        pattern = r'\$(\w+)\s+\$([0-9,]+(?:\.[0-9]+)?)\s+([\+\-][0-9\.]+)%\s+\|\s+([0-9]+)\s+RSI\s+\|\s+([0-9\.]+)x\s+ATR\s+\|\s+Z\s+([\+\-]?[0-9\.]+)\s+\|\s+Breakout'
        
        match = re.search(pattern, signal_text)
        if match:
            symbol = match.group(1)
            price_str = match.group(2).replace(',', '')
            price = float(price_str)
            change_pct = float(match.group(3))
            rsi = float(match.group(4))
            tr_atr = float(match.group(5))
            z_score = float(match.group(6))
            
            return {
                "symbol": symbol,
                "price": price,
                "change_pct": change_pct,
                "rsi": rsi,
                "tr_atr": tr_atr,
                "z_score": z_score
            }
        return None
    
    def should_buy(self, signal: Dict) -> bool:
        """Determine if we should buy based on signal strength"""
        # Buy criteria:
        # 1. RSI between 40-70 (not overbought/oversold)
        # 2. Z-score > 1.5 (strong momentum)
        # 3. TR/ATR > 1.5 (high volatility)
        # 4. Positive change percentage
        
        rsi = signal["rsi"]
        z_score = signal["z_score"]
        tr_atr = signal["tr_atr"]
        change_pct = signal["change_pct"]
        
        return (
            40 <= rsi <= 70 and
            z_score > 1.5 and
            tr_atr > 1.5 and
            change_pct > 0
        )
    
    def calculate_position_size(self, signal: Dict) -> int:
        """Calculate position size based on portfolio and signal strength"""
        account_info = self.get_account_info()
        portfolio_value = account_info.get("portfolio_value", 100000.0)
        
        # Base position size (10% of portfolio)
        base_position_value = portfolio_value * self.max_position_size
        
        # Adjust based on signal strength
        signal_strength = min(2.0, signal["z_score"] / 2.0)  # Normalize Z-score
        position_value = base_position_value * signal_strength
        
        # Calculate number of shares
        price = signal["price"]
        shares = int(position_value / price)
        
        return max(1, shares)  # Minimum 1 share
    
    def execute_buy_order(self, signal: Dict) -> bool:
        """Execute buy order for breakout signal"""
        try:
            symbol = signal["symbol"]
            shares = self.calculate_position_size(signal)
            
            # Check if we already have a position
            if symbol in self.portfolio["positions"]:
                print(f"Already have position in {symbol}, skipping", file=sys.stderr)
                return False
            
            # Create market order
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=shares,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            
            # Submit order
            order = self.trading_client.submit_order(order_request)
            
            # Update portfolio state
            self.portfolio["positions"][symbol] = {
                "shares": shares,
                "entry_price": signal["price"],
                "entry_time": datetime.now().isoformat(),
                "stop_loss": signal["price"] * (1 - self.stop_loss_pct),
                "take_profit": signal["price"] * (1 + self.take_profit_pct)
            }
            
            self.save_portfolio_state()
            
            print(f"✅ BUY ORDER: {shares} shares of {symbol} at ${signal['price']:.2f}")
            return True
            
        except Exception as e:
            print(f"❌ Buy order failed for {symbol}: {e}", file=sys.stderr)
            return False
    
    def check_exit_conditions(self):
        """Check if any positions should be sold"""
        try:
            for symbol, position in self.portfolio["positions"].items():
                # Get current price
                bars = self.data_client.get_stock_bars(
                    StockBarsRequest(
                        symbol_or_symbols=symbol,
                        timeframe=TimeFrame.Minute,
                        limit=1
                    )
                )
                
                if symbol in bars and bars[symbol]:
                    current_price = float(bars[symbol][-1].close)
                    entry_price = position["entry_price"]
                    stop_loss = position["stop_loss"]
                    take_profit = position["take_profit"]
                    
                    # Check stop loss
                    if current_price <= stop_loss:
                        self.execute_sell_order(symbol, "Stop Loss")
                        continue
                    
                    # Check take profit
                    if current_price >= take_profit:
                        self.execute_sell_order(symbol, "Take Profit")
                        continue
                    
                    # Check RSI exit (if RSI > 80, consider selling)
                    # This would require additional data fetching
                    
        except Exception as e:
            print(f"Error checking exit conditions: {e}", file=sys.stderr)
    
    def execute_sell_order(self, symbol: str, reason: str) -> bool:
        """Execute sell order"""
        try:
            if symbol not in self.portfolio["positions"]:
                return False
            
            position = self.portfolio["positions"][symbol]
            shares = position["shares"]
            
            # Create market order
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=shares,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )
            
            # Submit order
            order = self.trading_client.submit_order(order_request)
            
            # Remove from portfolio
            del self.portfolio["positions"][symbol]
            self.save_portfolio_state()
            
            print(f"✅ SELL ORDER: {shares} shares of {symbol} - {reason}")
            return True
            
        except Exception as e:
            print(f"❌ Sell order failed for {symbol}: {e}", file=sys.stderr)
            return False
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary"""
        account_info = self.get_account_info()
        positions = self.portfolio["positions"]
        
        total_positions = len(positions)
        total_value = account_info.get("portfolio_value", 0.0)
        cash = account_info.get("cash", 0.0)
        
        return {
            "total_value": total_value,
            "cash": cash,
            "positions_count": total_positions,
            "positions": list(positions.keys())
        }

def main():
    """Main paper trader function"""
    if len(sys.argv) < 2:
        print("Usage: paper_trader.py <breakout_signal>", file=sys.stderr)
        sys.exit(1)
    
    signal_text = sys.argv[1]
    
    trader = PaperTrader()
    signal = trader.parse_breakout_signal(signal_text)
    
    if not signal:
        print("❌ Could not parse breakout signal", file=sys.stderr)
        sys.exit(1)
    
    print(f"📊 Analyzing signal: {signal['symbol']} at ${signal['price']:.2f}")
    
    # Check exit conditions for existing positions
    trader.check_exit_conditions()
    
    # Check if we should buy
    if trader.should_buy(signal):
        print(f"🎯 Signal meets buy criteria - executing buy order")
        trader.execute_buy_order(signal)
    else:
        print(f"❌ Signal does not meet buy criteria")
    
    # Show portfolio summary
    summary = trader.get_portfolio_summary()
    print(f"💰 Portfolio: ${summary['total_value']:,.2f} | Cash: ${summary['cash']:,.2f} | Positions: {summary['positions_count']}")

if __name__ == "__main__":
    main()
