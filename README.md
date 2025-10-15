# Asymmetric Trading System

A modular trading and market analysis system organized into three main domains.

## Structure

### `analyst/` - Market Data & Analysis
- **`alpaca/`** - Alpaca Markets integration for real-time data
- **`database/`** - SQLite database for signal storage
- **`tests/`** - Unit tests for the system
- **Shell scripts**: `start_auto_trader.sh`, `stop_auto_trader.sh`, `status.sh`

### `output/` - External Communication
- **`gmail/`** - Email notifications and alerts
- **`x/`** - Twitter/X posting with rate limiting

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
```

### 4. Twitter/X Integration
```bash
cd output/x/scripts
python3 rate_limit_status.py  # Check rate limits
python3 tweet_with_limit.py   # Send tweets with rate limiting
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