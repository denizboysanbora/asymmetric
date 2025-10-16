#!/usr/bin/env python3
"""
Investor Trading Executor
Executes trades based on analyst signals using Alpaca API
"""
import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

load_dotenv()

class TradingExecutor:
    def __init__(self):
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        if not self.api_key or not self.secret_key:
            raise RuntimeError("Missing ALPACA_API_KEY or ALPACA_SECRET_KEY")
        
        self.client = TradingClient(self.api_key, self.secret_key, paper=True)
    
    def get_portfolio(self):
        """Get current portfolio positions"""
        try:
            positions = self.client.get_all_positions()
            if not positions:
                return "No positions"
            
            portfolio_info = []
            for position in positions:
                portfolio_info.append(f"{position.symbol}: {position.qty} shares @ ${position.avg_entry_price}")
            
            return "; ".join(portfolio_info)
        except Exception as e:
            return f"Error getting portfolio: {e}"
    
    def execute_trade(self, symbol, price, change_pct, asset_class):
        """Execute trade based on signal"""
        try:
            # Determine order side based on signal
            side = OrderSide.BUY if change_pct > 0 else OrderSide.SELL
            
            # Calculate position size (example: 1% of portfolio per signal)
            # This is a simplified example - real implementation would be more sophisticated
            account = self.client.get_account()
            buying_power = float(account.buying_power)
            position_size = min(buying_power * 0.01, 1000)  # Max $1000 per trade
            
            # Calculate quantity
            quantity = int(position_size / price)
            if quantity < 1:
                return f"Insufficient buying power for {symbol}"
            
            # Create market order
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=side,
                time_in_force=TimeInForce.DAY
            )
            
            # Submit order
            order = self.client.submit_order(order_data)
            return f"Order submitted: {side} {quantity} {symbol} @ market price (Order ID: {order.id})"
            
        except Exception as e:
            return f"Trade execution failed: {e}"
    
    def risk_check(self):
        """Perform risk management checks"""
        try:
            account = self.client.get_account()
            positions = self.client.get_all_positions()
            
            risk_info = []
            risk_info.append(f"Account Value: ${account.portfolio_value}")
            risk_info.append(f"Buying Power: ${account.buying_power}")
            risk_info.append(f"Positions: {len(positions)}")
            
            # Check for over-concentration
            total_value = float(account.portfolio_value)
            for position in positions:
                position_value = float(position.market_value)
                concentration = (position_value / total_value) * 100
                if concentration > 10:  # More than 10% in one position
                    risk_info.append(f"WARNING: {position.symbol} is {concentration:.1f}% of portfolio")
            
            return "; ".join(risk_info)
            
        except Exception as e:
            return f"Risk check failed: {e}"

def main():
    parser = argparse.ArgumentParser(description="Investor Trading Executor")
    parser.add_argument("--portfolio", action="store_true", help="Get portfolio status")
    parser.add_argument("--trade", nargs=4, metavar=("SYMBOL", "PRICE", "CHANGE_PCT", "ASSET_CLASS"), help="Execute trade")
    parser.add_argument("--risk-check", action="store_true", help="Perform risk management check")
    
    args = parser.parse_args()
    
    try:
        executor = TradingExecutor()
        
        if args.portfolio:
            result = executor.get_portfolio()
            print(result)
        
        elif args.trade:
            symbol, price, change_pct, asset_class = args.trade
            result = executor.execute_trade(symbol, float(price), float(change_pct), asset_class)
            print(result)
        
        elif args.risk_check:
            result = executor.risk_check()
            print(result)
        
        else:
            parser.print_help()
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()