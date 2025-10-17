#!/usr/bin/env python3
"""
Advanced Stock Scanner with Comprehensive Filters
"""
import os
import sys
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd

# Set API keys
os.environ['ALPACA_API_KEY'] = 'PK5KN56VW1TVTL7X2GSJ'
os.environ['ALPACA_SECRET_KEY'] = 'Ojsiz7lO4SgTHRLLHz2nYxEoitOaKL1sOmGXAcz3'

# Add alpaca directory to path
ALPACA_DIR = Path(__file__).parent.parent / "input" / "alpaca"
sys.path.insert(0, str(ALPACA_DIR))

try:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from alpaca.data.models import Bar
except ImportError as e:
    print(f"Error importing Alpaca modules: {e}")
    sys.exit(1)

class AdvancedStockScanner:
    """Advanced stock scanner with comprehensive filters"""
    
    def __init__(self):
        self.client = StockHistoricalDataClient(
            os.getenv('ALPACA_API_KEY'), 
            os.getenv('ALPACA_SECRET_KEY')
        )
        self.filters = {
            "price": "> $5",                     # Avoid penny stocks
            "avg_volume": "> 500,000",           # Needs liquidity
            "adr_percent": "> 5",                # Must move fast
            "relative_strength": "> 1.0",        # Outperforming market
            "revenue_growth_yoy": "> 25%",       # Explosive growth
            "market_cap": "> $300M",             # Tradable size
            "sector_strength": "Top 3 sectors",  # Rotational leadership
        }
    
    def get_all_tradable_stocks(self) -> List[str]:
        """Get all NYSE and NASDAQ stocks (limited by API access)"""
        # Note: Alpaca free tier doesn't provide full stock universe
        # This would require a premium data provider like Polygon, IEX, or Quandl
        
        # For now, we'll use an expanded list of liquid stocks
        return [
            # Mega Cap Tech
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'NFLX', 'AMD', 'INTC',
            # Growth & Cloud
            'CRM', 'ADBE', 'PYPL', 'UBER', 'LYFT', 'SQ', 'ROKU', 'ZM', 'PTON', 'SPOT',
            # Crypto & Fintech
            'COIN', 'PLTR', 'SNOW', 'CRWD', 'OKTA', 'NET', 'DDOG', 'ZS', 'MDB', 'TEAM',
            # AI & Semiconductors
            'AVGO', 'QCOM', 'TXN', 'ADI', 'MRVL', 'LRCX', 'KLAC', 'AMAT', 'MU', 'WDC',
            # Biotech & Healthcare
            'GILD', 'AMGN', 'BIIB', 'REGN', 'VRTX', 'ILMN', 'MRNA', 'BNTX', 'PFE', 'JNJ',
            # Energy & Materials
            'XOM', 'CVX', 'COP', 'EOG', 'SLB', 'HAL', 'NEE', 'DUK', 'SO', 'AEP',
            # Financials
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'AXP', 'V', 'MA',
            # Consumer & Retail
            'WMT', 'HD', 'PG', 'KO', 'PEP', 'NKE', 'SBUX', 'MCD', 'DIS',
            # Emerging Growth
            'RBLX', 'U', 'SNOW', 'DDOG', 'NET', 'ZS', 'CRWD', 'OKTA', 'PLTR', 'COIN',
            # Additional Liquid Stocks
            'ABNB', 'ADSK', 'AEP', 'AMAT', 'AMD', 'AMGN', 'AMT', 'ANET', 'ANSS', 'AON',
            'AVGO', 'AXP', 'AZO', 'BA', 'BABA', 'BAC', 'BDX', 'BIIB', 'BK', 'BKNG',
            'BLK', 'BMY', 'BRK.B', 'BSX', 'C', 'CAT', 'CB', 'CCI', 'CDNS', 'CHTR',
            'CL', 'CMCSA', 'COF', 'COP', 'COST', 'CPRT', 'CRM', 'CSCO', 'CSGP', 'CSX',
            'CTAS', 'CTSH', 'CVS', 'CVX', 'D', 'DAL', 'DD', 'DE', 'DHR', 'DIS',
            'DISH', 'DLTR', 'DOV', 'DRE', 'DUK', 'DVA', 'DVN', 'DXCM', 'EA', 'EBAY',
            'ECL', 'ED', 'EFX', 'EIX', 'EL', 'EMN', 'EMR', 'ENPH', 'EOG', 'EQIX',
            'EQR', 'ES', 'ESS', 'ETN', 'ETR', 'EVRG', 'EW', 'EXC', 'EXPD', 'EXR',
            'F', 'FANG', 'FAST', 'FB', 'FBHS', 'FCX', 'FDX', 'FE', 'FFIV', 'FIS',
            'FISV', 'FITB', 'FLT', 'FMC', 'FOX', 'FOXA', 'FRC', 'FRT', 'FTNT', 'FTV',
            'GD', 'GE', 'GILD', 'GIS', 'GL', 'GLW', 'GM', 'GOOG', 'GOOGL', 'GPN',
            'GPS', 'GRMN', 'GS', 'GWW', 'HAL', 'HAS', 'HBAN', 'HCA', 'HD', 'HES',
            'HIG', 'HOLX', 'HON', 'HPE', 'HPQ', 'HRB', 'HRL', 'HSIC', 'HST', 'HSY',
            'HUM', 'HWM', 'IBM', 'ICE', 'IDXX', 'IEX', 'IFF', 'ILMN', 'INCY', 'INFO',
            'INTC', 'INTU', 'INVH', 'IP', 'IPG', 'IQV', 'IR', 'IRM', 'IS', 'ISRG',
            'IT', 'ITW', 'IVZ', 'JBHT', 'JCI', 'JKHY', 'JNJ', 'JNPR', 'JPM', 'JWN',
            'K', 'KDP', 'KEM', 'KEY', 'KEYS', 'KHC', 'KIM', 'KLAC', 'KMB', 'KMI',
            'KMX', 'KO', 'KR', 'KSU', 'L', 'LB', 'LDOS', 'LEG', 'LEN', 'LH',
            'LHX', 'LIN', 'LKQ', 'LLY', 'LMT', 'LNC', 'LNT', 'LOW', 'LRCX', 'LUV',
            'LVS', 'LW', 'LYB', 'LYV', 'MA', 'MAA', 'MAR', 'MAS', 'MCD', 'MCHP',
            'MCK', 'MCO', 'MDLZ', 'MDT', 'MET', 'META', 'MGM', 'MHK', 'MKC', 'MKTX',
            'MLM', 'MMC', 'MMM', 'MNST', 'MO', 'MOH', 'MOS', 'MPC', 'MPWR', 'MRK',
            'MRNA', 'MRO', 'MS', 'MSCI', 'MSFT', 'MSI', 'MTB', 'MTD', 'MU', 'NCLH',
            'NDAQ', 'NDSN', 'NEE', 'NEM', 'NFLX', 'NI', 'NKE', 'NLOK', 'NLSN', 'NOC',
            'NOW', 'NRG', 'NSC', 'NTAP', 'NTRS', 'NUE', 'NVDA', 'NVR', 'NWL', 'NWS',
            'NWSA', 'NXPI', 'O', 'ODFL', 'OGN', 'OKE', 'OMC', 'ON', 'ORCL', 'ORLY',
            'OTIS', 'OXY', 'PAYC', 'PAYX', 'PCAR', 'PCG', 'PEAK', 'PEG', 'PENN', 'PEP',
            'PFE', 'PG', 'PGR', 'PH', 'PHM', 'PKG', 'PKI', 'PLD', 'PM', 'PNC',
            'PNR', 'PNW', 'POOL', 'PPG', 'PPL', 'PRU', 'PSA', 'PSX', 'PTC', 'PTON',
            'PWR', 'PXD', 'PYPL', 'QCOM', 'QRVO', 'RCL', 'RE', 'REG', 'REGN', 'RF',
            'RHI', 'RJF', 'RL', 'RMD', 'ROK', 'ROL', 'ROP', 'ROST', 'RSG', 'RTX',
            'SBAC', 'SBUX', 'SCHW', 'SEDG', 'SEE', 'SHW', 'SIVB', 'SJM', 'SLB', 'SNA',
            'SNPS', 'SO', 'SPG', 'SPGI', 'SRE', 'STE', 'STT', 'STX', 'STZ', 'SWK',
            'SWKS', 'SYF', 'SYK', 'SYY', 'T', 'TAP', 'TDG', 'TDY', 'TECH', 'TEL',
            'TER', 'TFC', 'TFX', 'TGT', 'TMO', 'TMUS', 'TPG', 'TROW', 'TRV', 'TSCO',
            'TSLA', 'TSN', 'TT', 'TTWO', 'TWTR', 'TXN', 'TXT', 'TYL', 'UAA', 'UAL',
            'UDR', 'UHS', 'ULTA', 'UNH', 'UNP', 'UPS', 'URI', 'USB', 'V', 'VFC',
            'VICI', 'VLO', 'VMC', 'VRSK', 'VRSN', 'VRTX', 'VTR', 'VTRS', 'VZ', 'WAB',
            'WAT', 'WBA', 'WEC', 'WELL', 'WFC', 'WHR', 'WLTW', 'WM', 'WMB', 'WMT',
            'WRB', 'WU', 'WY', 'WYNN', 'XEL', 'XLNX', 'XOM', 'XRAY', 'XYL', 'YUM',
            'ZBH', 'ZBRA', 'ZION', 'ZTS'
        ]
    
    def calculate_adr_percent(self, bars: List[Bar]) -> float:
        """Calculate Average Daily Range percentage"""
        if len(bars) < 20:
            return 0.0
        
        recent_bars = bars[-20:]
        ranges = []
        for bar in recent_bars:
            daily_range = (bar.high - bar.low) / bar.low * 100
            ranges.append(daily_range)
        
        return np.mean(ranges)
    
    def calculate_relative_strength(self, stock_bars: List[Bar], spy_bars: List[Bar]) -> float:
        """Calculate relative strength vs SPY"""
        if len(stock_bars) < 20 or len(spy_bars) < 20:
            return 1.0
        
        stock_returns = []
        spy_returns = []
        
        for i in range(1, min(len(stock_bars), len(spy_bars))):
            stock_return = (stock_bars[i].close - stock_bars[i-1].close) / stock_bars[i-1].close
            spy_return = (spy_bars[i].close - spy_bars[i-1].close) / spy_bars[i-1].close
            stock_returns.append(stock_return)
            spy_returns.append(spy_return)
        
        if len(stock_returns) == 0:
            return 1.0
        
        stock_performance = np.mean(stock_returns)
        spy_performance = np.mean(spy_returns)
        
        if spy_performance == 0:
            return 1.0
        
        return stock_performance / spy_performance
    
    def apply_filters(self, symbol: str, bars: List[Bar], spy_bars: List[Bar]) -> Dict:
        """Apply all filters to a stock"""
        if len(bars) < 20:
            return {"passed": False, "reasons": ["Insufficient data"]}
        
        latest_bar = bars[-1]
        results = {
            "symbol": symbol,
            "price": latest_bar.close,
            "passed": True,
            "reasons": []
        }
        
        # Filter 1: Price > $5
        if latest_bar.close <= 5.0:
            results["passed"] = False
            results["reasons"].append(f"Price ${latest_bar.close:.2f} <= $5")
        
        # Filter 2: Average Volume > 500,000
        recent_volumes = [bar.volume for bar in bars[-20:]]
        avg_volume = np.mean(recent_volumes)
        if avg_volume <= 500000:
            results["passed"] = False
            results["reasons"].append(f"Avg volume {avg_volume:,.0f} <= 500,000")
        
        # Filter 3: ADR > 5%
        adr_percent = self.calculate_adr_percent(bars)
        if adr_percent <= 5.0:
            results["passed"] = False
            results["reasons"].append(f"ADR {adr_percent:.1f}% <= 5%")
        
        # Filter 4: Relative Strength > 1.0
        rs = self.calculate_relative_strength(bars, spy_bars)
        if rs <= 1.0:
            results["passed"] = False
            results["reasons"].append(f"RS {rs:.2f} <= 1.0")
        
        # Note: Revenue growth and market cap filters would require fundamental data
        # which is not available in the free Alpaca tier
        
        results["adr_percent"] = adr_percent
        results["relative_strength"] = rs
        results["avg_volume"] = avg_volume
        
        return results
    
    def scan_stocks(self, max_stocks: int = 500) -> List[Dict]:
        """Scan stocks with advanced filters"""
        print(f"🔍 Advanced Stock Scanner with Filters")
        print(f"📊 Filters: {self.filters}")
        print(f"🎯 Scanning up to {max_stocks} stocks...")
        
        # Get SPY data for relative strength calculation
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            
            spy_request = StockBarsRequest(
                symbol_or_symbols="SPY",
                timeframe=TimeFrame.Day,
                start=start_date,
                end=end_date
            )
            
            spy_data = self.client.get_stock_bars(spy_request)
            spy_bars = spy_data.data["SPY"] if "SPY" in spy_data.data else []
            
            print(f"📈 Loaded {len(spy_bars)} SPY bars for benchmark")
            
        except Exception as e:
            print(f"❌ Error loading SPY data: {e}")
            return []
        
        # Get all tradable stocks
        all_stocks = self.get_all_tradable_stocks()
        stocks_to_scan = all_stocks[:max_stocks]
        
        results = []
        
        for i, symbol in enumerate(stocks_to_scan):
            try:
                print(f"📊 Analyzing {symbol} ({i+1}/{len(stocks_to_scan)})...", end=" ")
                
                # Get stock data
                request = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=TimeFrame.Day,
                    start=start_date,
                    end=end_date
                )
                
                bars_data = self.client.get_stock_bars(request)
                
                if not bars_data or symbol not in bars_data.data:
                    print("❌ No data")
                    continue
                
                bars = bars_data.data[symbol]
                
                if len(bars) < 20:
                    print("❌ Insufficient data")
                    continue
                
                # Apply filters
                filter_results = self.apply_filters(symbol, bars, spy_bars)
                
                if filter_results["passed"]:
                    print("✅ PASSED")
                    results.append(filter_results)
                else:
                    print(f"❌ FAILED: {', '.join(filter_results['reasons'])}")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
        
        return results

def main():
    """Main advanced scanner"""
    scanner = AdvancedStockScanner()
    
    print("🚀 Starting Advanced Stock Scanner")
    print("=" * 50)
    
    # Scan stocks
    results = scanner.scan_stocks(max_stocks=500)  # Scan first 500 stocks
    
    print("\n" + "=" * 50)
    print(f"📊 SCAN RESULTS: {len(results)} stocks passed all filters")
    print("=" * 50)
    
    if results:
        print("\n🎯 FILTERED STOCKS:")
        for result in results:
            print(f"✅ {result['symbol']}: ${result['price']:.2f} | "
                  f"ADR: {result['adr_percent']:.1f}% | "
                  f"RS: {result['relative_strength']:.2f} | "
                  f"Vol: {result['avg_volume']:,.0f}")
    else:
        print("❌ No stocks passed all filters")
    
    print(f"\n📈 Total stocks analyzed: 500")
    print(f"✅ Stocks passing filters: {len(results)}")
    print(f"📊 Success rate: {len(results)/500*100:.1f}%")

if __name__ == "__main__":
    main()
