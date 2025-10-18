# Breakout Scanner

A focused automated trading signal system that scans for breakout setups using technical analysis and sends email notifications.

## 🎯 System Overview

### **Analyst Mode** - Breakout Detection
- **Purpose**: Scan markets for breakout setups
- **Schedule**: 10 AM - 4 PM Eastern Time (weekdays only)
- **Assets**: Stocks only
- **Strategy**: Breakout methodology
- **Output**: Console output + Email notifications

## 📁 Project Structure

```
asymmetric/
├── analyst/                    # Analyst modules
│   ├── breakout/               # Flag Breakout Analyst
│   │   ├── breakout_analyst.sh # Main breakout scanner
│   │   ├── breakout_scanner.py # Breakout detection logic
│   │   ├── start.sh            # Start breakout analyst
│   │   ├── stop.sh             # Stop breakout analyst
│   │   └── status.sh           # Breakout analyst status
│   ├── config/                 # Shared configuration
│   ├── input/alpaca/           # Shared Alpaca integration
│   ├── output/gmail/           # Shared email functionality
│   └── docs/                   # Documentation
├── investor/                   # Paper Trading
│   ├── investor.sh            # Main investment script
│   ├── paper_trader.py        # Paper trading logic
│   ├── logs/                  # Investment logs
│   ├── start.sh              # Start script
│   ├── stop.sh               # Stop script
│   └── status.sh             # Status checker
└── (space for future analyst modules)
```

## 🚀 Quick Start

### Start Both Modes
```bash
# Start Breakout Analyst
./analyst/breakout/start.sh

# Start Investor (Paper Trading)
./investor/start.sh
```

### Check Status
```bash
# Check breakout analyst
./analyst/breakout/status.sh

# Check investor
./investor/status.sh
```

### Stop Modes
```bash
./analyst/breakout/stop.sh
./investor/stop.sh
```

## 📊 Breakout Strategy

### Signal Detection
The system detects breakout setups based on:

1. **Prior Impulse**: 30%+ move in the last 60 days
2. **Tight Flag Consolidation**: Last 20 days showing:
   - Higher lows pattern
   - ATR contraction (reduced volatility)
   - Consolidation after impulse

### Technical Indicators
- **RSI**: Relative Strength Index
- **ATR**: Average True Range
- **Z-Score**: Volatility measure
- **ADR**: Average Daily Range percentage

### Signal Format
```
$SYMBOL $PRICE +X.X% | ## RSI | X.XXx ATR | Z X.X | Breakout
```

Examples:
- `$NVDA $450.25 +2.3% | 65 RSI | 2.10x ATR | Z 1.8 | Breakout`
- `$TSLA $250.50 +1.7% | 58 RSI | 1.90x ATR | Z 1.2 | Breakout`

## 💰 Paper Trading

### Investment Logic
The investor module executes paper trades based on breakout signals:

1. **Buy Criteria**:
   - RSI between 40-70 (not overbought/oversold)
   - Z-score > 1.5 (strong momentum)
   - TR/ATR > 1.5 (high volatility)
   - Positive change percentage

2. **Position Sizing**: 10% of portfolio per position
3. **Risk Management**:
   - 5% stop loss
   - 15% take profit
   - Automatic exit conditions

### Portfolio Management
- **Starting Capital**: $100,000
- **Position Tracking**: JSON state file
- **Real-time Monitoring**: Alpaca paper trading API

## 📧 Email Notifications

### Email Setup
1. **Gmail API**: `analyst/output/gmail/token.json`
   - Run: `python3 analyst/output/gmail/scripts/gmail_auth.py`
   - Requires OAuth2 credentials from Google Cloud Console

2. **Recipient**: `deniz@bora.box`
3. **Subject**: "Flag Breakout Signal"
4. **Content**: Clean signal format only

## ⏰ Schedule & Automation

### Operating Hours
- **Schedule**: 10 AM - 4 PM Eastern Time
- **Frequency**: Every 30 minutes during operating hours
- **Market awareness**: Only processes stocks during market hours

### Automation
- **Process locking**: Prevents duplicate executions
- **Error handling**: Comprehensive logging and fault tolerance

## 🔧 Configuration

### Required API Keys
1. **Alpaca Markets**: `analyst/input/alpaca/.env`
   ```
   ALPACA_API_KEY=your_key
   ALPACA_SECRET_KEY=your_secret
   ```

2. **Gmail API**: `analyst/output/gmail/token.json`
   - Run: `python3 analyst/output/gmail/scripts/gmail_auth.py`

## 📈 Monitoring

### View Logs
```bash
# Breakout analyst logs
tail -f analyst/breakout/logs/breakout_analyst.log

# Investor logs
tail -f investor/logs/investor.log
```

### Check Status
```bash
# Breakout analyst status
./analyst/breakout/status.sh

# Investor status
./investor/status.sh
```

## 🎯 Key Features

1. **Focused Strategy**: Only breakout setups
2. **Real-time Detection**: 30-minute scanning intervals during operating hours
3. **Stock-only Support**: Focused on liquid stocks
4. **Email Notifications**: Gmail integration for signal alerts
5. **Paper Trading**: Automated investment execution
6. **Market Awareness**: Only scans stocks during market hours
7. **Fault Tolerance**: Process locking, error handling
8. **Clean Output**: Console + email output format
9. **Modular Design**: Easy to add new analyst modules

## 🔄 Workflow

1. **Breakout Analyst**:
   - Scans markets every 30 minutes during operating hours
   - Detects breakout setups
   - Sends email notifications
   - Outputs signals to console
   - Logs all activity

2. **Investor Mode**:
   - Monitors analyst logs for breakout signals
   - Executes paper trades based on signal strength
   - Manages portfolio positions
   - Implements risk management

## 📞 Support

- **Breakout Analyst Status**: `./analyst/breakout/status.sh`
- **Investor Status**: `./investor/status.sh`
- **Logs**: Check log files
- **API Limits**: Built-in monitoring tools

---

**Version**: 6.0 (Analysts + Paper Trading)  
**Status**: Production Ready ✅
