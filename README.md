# Asymmetric Trading System

A modular trading and market analysis system organized into three main domains.

## Structure

### `analyst/` - Market Data & Analysis
- **`alpaca/`** - Alpaca Markets integration for real-time data
- **`database/`** - SQLite database for signal storage
- **`tests/`** - Unit tests for the system
- **`fetch_btc_price.py`** - Live BTC price fetcher
- **Shell scripts**: `start_auto_trader.sh`, `stop_auto_trader.sh`, `status.sh`

### `output/` - External Communication
- **`gmail/`** - Email notifications and alerts
- **`x/`** - Twitter/X posting with rate limiting
- **`chat/`** - Web interface for signal visualization
- **`email_btc_snapshot.py`** - BTC price email sender

### `investor/` - Trading Strategies
- **`investor_backend/`** - Core command execution engine
- **`trader/`** - Legacy trader tools and scripts
- **`execute_command.py`** - Main entry point for investor commands

## Quick Start

### 1. Market Data Analysis
```bash
# Start automated scanning
cd analyst
./start_auto_trader.sh

# Check status
./status.sh

# Stop scanning
./stop_auto_trader.sh
```

### 2. Investor Commands
```bash
# Scan a stock
cd investor
python3 execute_command.py "scan AAPL"

# Email a signal
python3 execute_command.py "email TSLA"

# Tweet a signal
python3 execute_command.py "tweet NVDA"
```

### 3. BTC Email Test
```bash
# Send live BTC price email (requires Gmail auth)
python3 output/email_btc_snapshot.py you@example.com
```

### 4. Chat Interface
```bash
cd output/chat
npm install
npm run dev
# API available at http://localhost:5174
```

## Configuration

### Required Credentials
1. **Alpaca API**: `analyst/alpaca/alpaca-mcp-server/.env`
2. **Gmail API**: `output/gmail/config/token.json`
3. **Twitter API**: `output/x/config/` (optional)

### Gmail Setup
```bash
cd output/gmail/scripts
python3 gmail_auth.py
# Follow OAuth flow to generate token.json
```

## Documentation
- **Setup**: `analyst/SETUP_FIXES.md`
- **Usage**: `analyst/USAGE.md`
- **System**: `analyst/SYSTEM_SUMMARY.md`

## Key Features
- Real-time market data via Alpaca
- Technical analysis with ATR and Z-scores
- Automated scanning (stocks weekdays, crypto weekends)
- Rate-limited social media posting
- Email notifications
- SQLite signal storage
- Web-based signal visualization