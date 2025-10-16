# Asymmetric Trading System

A comprehensive automated trading system with two distinct modes: **Analyst** (market analysis & signal generation) and **Investor** (trading execution & portfolio management).

## 🎯 System Overview

### **Analyst Mode** - Market Analysis & Signal Generation
- **Purpose**: Scan markets and generate trading signals
- **Schedule**: 8 AM - 5 PM Eastern Time
- **Assets**: Both stocks and crypto
- **Outputs**: Email alerts + Twitter posts
- **No Trading**: Pure analysis and signal generation

### **Investor Mode** - Trading Execution & Portfolio Management  
- **Purpose**: Execute trades based on analyst signals
- **Schedule**: 8 AM - 5 PM Eastern Time
- **Function**: Uses Alpaca API for actual market transactions
- **Trading Logic**: Buy/sell decisions based on analyst signals

## 📁 Project Structure

```
asymmetric/
├── analyst/                    # Market Analysis & Signal Generation
│   ├── scanner/               # Stock & crypto scanning logic
│   │   ├── compute_spike_params.py
│   │   ├── compute_spike_params_stocks.py
│   │   ├── check_market_open.py
│   │   └── venv/
│   ├── signals/               # Signal processing & formatting
│   ├── notifications/         # Email & Twitter integration
│   │   ├── scripts/
│   │   │   ├── send_email.py
│   │   │   ├── tweet_with_limit.py
│   │   │   └── tweet_hourly_summary.py
│   │   └── config/
│   ├── database/             # Signal logging & storage
│   │   ├── log_signal.py
│   │   └── signals.db
│   ├── analyst.sh           # Main analyst orchestration
│   └── logs/
└── investor/                 # Trading Execution
    ├── trading/              # Alpaca trading API integration
    │   └── executor.py
    ├── portfolio/            # Position management
    ├── execution/            # Order execution logic
    ├── investor.sh          # Main investor orchestration
    └── logs/
```

## 🚀 Quick Start

### Start Analyst Mode
```bash
./start_analyst.sh
```

### Start Investor Mode
```bash
./start_investor.sh
```

### Check Status
```bash
./status.sh
```

### Stop Modes
```bash
./stop_analyst.sh
./stop_investor.sh
```

## 📊 Technical Analysis

### Signal Detection
- **True Range (TR)**: `max(high-low, |high-prev_close|, |low-prev_close|)`
- **Average True Range (ATR)**: 14-period exponential moving average
- **TR/ATR Ratio**: Current volatility vs. average volatility
- **Z-Score**: Standard deviations from mean return
- **24-hour Price Change**: Percentage move

### Signal Classification
**Stock Thresholds:**
- TR/ATR > 2.0 (volatility 2x above average)
- |Z-Score| > 2.0 (2 standard deviations)
- |Price Change| > 2%

**Crypto Thresholds:**
- TR/ATR > 2.0
- |Z-Score| > 2.0  
- |Price Change| > 2%

## 📱 Output Format

### Signal Format
```
$SYMBOL $PRICE +X.XX% | X.XXx ATR | Z X.XX | Breakout
```

Examples:
- `$BTC $67,450 +2.45% | 2.25x ATR | Z 2.24 | Breakout`
- `$NVDA $183.15 +2.52% | 2.18x ATR | Z 2.45 | Breakout`

### Communication Channels
1. **Email Alerts** (Gmail API)
   - Recipient: `deniz@bora.box`
   - Subject: "Signal"
   - Immediate delivery for each signal

2. **Twitter/X Posting** (OAuth1)
   - Rate limited: 17 tweets per 24 hours
   - Individual tweets for each signal

3. **Database Logging** (SQLite)
   - Stores all signals with timestamps
   - Tracks: symbol, price, change%, TR/ATR, Z-score, signal type, asset class

## ⏰ Schedule & Automation

### Operating Hours
- **Schedule**: 8 AM - 5 PM Eastern Time
- **Both modes**: Analyst and Investor run during these hours
- **Market awareness**: Only processes stocks during market hours

### Automation
- **Cron jobs**: Can be set up to run every 5 minutes during operating hours
- **Process locking**: Prevents duplicate executions
- **Error handling**: Comprehensive logging and fault tolerance

## 🔧 Configuration

### Required API Keys
1. **Alpaca Markets**: `analyst/scanner/.env`
   ```
   ALPACA_API_KEY=your_key
   ALPACA_SECRET_KEY=your_secret
   ```

2. **Gmail API**: `analyst/notifications/config/token.json`
   - Run: `python3 analyst/notifications/scripts/gmail_auth.py`

3. **Twitter API**: `analyst/notifications/config/`
   - OAuth1 credentials for tweeting

### Database Setup
```bash
cd analyst/database
python3 init_db.py
```

## 📈 Monitoring

### View Logs
```bash
# Analyst logs
tail -f analyst/logs/analyst.log

# Investor logs  
tail -f investor/logs/investor.log
```

### Database Queries
```bash
# View recent signals
sqlite3 analyst/database/signals.db "SELECT * FROM signals ORDER BY timestamp DESC LIMIT 10;"

# Count signals by asset class
sqlite3 analyst/database/signals.db "SELECT asset_class, COUNT(*) FROM signals GROUP BY asset_class;"
```

### Rate Limiting
```bash
# Check Twitter rate limits
cd analyst/notifications
python3 scripts/rate_limit_status.py
```

## 🎯 Key Features

1. **Two-Mode Architecture**: Clear separation between analysis and execution
2. **Real-time Detection**: 5-minute scanning intervals during operating hours
3. **Multi-asset Support**: Both stocks and crypto
4. **Rate Limiting**: Respects API limits (17 tweets/24h)
5. **Market Awareness**: Only scans stocks during market hours
6. **Historical Tracking**: Complete database logging
7. **Fault Tolerance**: Process locking, error handling
8. **Dynamic Asset Lists**: Automatically detects available symbols

## 🔄 Workflow

1. **Analyst Mode**:
   - Scans markets every 5 minutes during operating hours
   - Generates signals based on technical analysis
   - Sends email alerts and tweets
   - Logs all signals to database

2. **Investor Mode**:
   - Monitors database for recent signals
   - Executes trades based on signal strength
   - Manages portfolio positions
   - Performs risk management checks

## 📞 Support

- **System Status**: `./status.sh`
- **Logs**: Check respective log files
- **Database**: SQLite queries for signal analysis
- **API Limits**: Built-in monitoring tools

---

**Version**: 3.0 (Restructured)  
**Status**: Production Ready ✅