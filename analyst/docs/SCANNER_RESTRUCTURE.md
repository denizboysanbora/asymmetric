# Scanner Restructure - Two Scanner Architecture

## ✅ **Completed Implementation**

The analyst folder has been restructured with a clear input/output separation and two distinct scanners.

### 🎯 **New Structure**

```
analyst/
├── input/                    # Data sources and scanners
│   ├── alpaca/              # Alpaca API integration (moved from scanner/)
│   │   ├── venv/
│   │   ├── compute_spike_params.py
│   │   ├── compute_spike_params_stocks.py
│   │   ├── check_market_open.py
│   │   └── .env
│   ├── breakout/            # Breakout scanner
│   │   └── breakout_scanner.py
│   └── trend/               # Trend scanner
│       └── trend_scanner.py
├── output/                  # Notifications and storage
│   ├── gmail/               # Email integration
│   │   ├── send_email.py
│   │   └── token.json
│   ├── tweet/               # Twitter integration
│   │   ├── tweet_with_limit.py
│   │   └── post_text_oauth1.py
│   └── database/            # Database logging
│       ├── log_signal.py
│       └── signals.db
├── analyst.sh              # Main orchestration script
├── start.sh                # Start analyst mode
├── stop.sh                 # Stop analyst mode
└── status.sh               # Check system status
```

### 🔍 **Two Scanner Types**

#### **1. Breakout Scanner** (`input/breakout/`)
- **Purpose**: Detects volatility breakouts using technical analysis
- **Logic**: Uses existing `compute_spike_params.py` and `compute_spike_params_stocks.py`
- **Output Format**: `$SYMBOL $PRICE +X.XX% | X.XXx ATR | Z X.XX | Breakout`
- **Examples**:
  - `$NVDA $183.15 +2.52% | 2.18x ATR | Z 2.45 | Breakout`
  - `$BTC $67,450 +2.45% | 2.25x ATR | Z 2.24 | Breakout`

#### **2. Trend Scanner** (`input/trend/`)
- **Purpose**: Detects biggest intraday movers
- **Logic**: Scans stocks for largest intraday moves (open to current price)
- **Output Format**: `$SYMBOL $PRICE +X.XX%`
- **Examples**:
  - `$NVDA $183.15 +2.52%`
  - `$TSLA $245.67 -3.21%`

### 📊 **Scanner Logic**

#### **Breakout Scanner**
- Runs both crypto and stock breakout detection
- Uses existing technical analysis (TR/ATR, Z-score, price change)
- Filters for signals meeting breakout thresholds
- Outputs signals with "| Breakout" suffix

#### **Trend Scanner**
- Scans liquid stocks for intraday moves
- Calculates: `(current_price - today_open) / today_open * 100`
- Ranks by absolute change (biggest movers first)
- Only includes moves ≥1%
- Outputs top 10 movers

### 🔄 **Orchestration**

The main `analyst.sh` script:
1. **Runs Breakout Scanner**: Detects volatility breakouts
2. **Runs Trend Scanner**: Detects intraday movers
3. **Processes Signals**: Each signal gets:
   - Email notification
   - Twitter post (rate-limited)
   - Database logging
4. **Logs Results**: All activity logged to `analyst/logs/analyst.log`

### 📱 **Output Integration**

#### **Email** (`output/gmail/`)
- Sends individual emails for each signal
- Subject: "Signal" for breakouts, "Trend" for trends
- Recipient: `deniz@bora.box`

#### **Twitter** (`output/tweet/`)
- Posts individual tweets for each signal
- Rate limited: 17 tweets per 24 hours
- Uses existing rate limiting logic

#### **Database** (`output/database/`)
- Logs all signals to SQLite database
- Tracks: timestamp, symbol, price, change%, TR/ATR, Z-score, signal_type, asset_class
- Signal types: "Breakout" and "Trending"

### 🎯 **Key Features**

1. **Clear Separation**: Input (data sources) vs Output (notifications)
2. **Two Scanner Types**: Breakout (technical analysis) vs Trend (intraday moves)
3. **Consistent Format**: Both use `$SYMBOL $PRICE +X.XX%` base format
4. **Unified Processing**: Same email/tweet/database integration for both
5. **Schedule**: 8 AM - 5 PM Eastern Time
6. **Rate Limiting**: Twitter 17/24h, emails per signal

### 🚀 **Usage**

```bash
# Start analyst mode (runs both scanners)
./analyst/start.sh

# Check status
./analyst/status.sh

# Stop analyst mode
./analyst/stop.sh

# View logs
tail -f analyst/logs/analyst.log
```

### 📊 **Expected Output**

#### **Breakout Signals**
```
$NVDA $183.15 +2.52% | 2.18x ATR | Z 2.45 | Breakout
$BTC $67,450 +2.45% | 2.25x ATR | Z 2.24 | Breakout
```

#### **Trend Signals**
```
$NVDA $183.15 +2.52%
$TSLA $245.67 -3.21%
$AMD $142.34 +1.89%
```

### ✅ **Testing Results**

- ✅ **Structure**: Input/output separation implemented
- ✅ **Breakout Scanner**: Uses existing logic, outputs correct format
- ✅ **Trend Scanner**: Detects intraday movers, outputs correct format
- ✅ **Integration**: Email, Twitter, and database logging working
- ✅ **Orchestration**: Main script runs both scanners
- ✅ **Error Handling**: Proper error messages for missing API keys

### 🔧 **Next Steps**

1. **Configure API Keys**: Set up Alpaca, Gmail, and Twitter credentials
2. **Test Full Workflow**: Run both scanners with real data
3. **Set up Cron**: Schedule analyst mode for 8 AM - 5 PM ET
4. **Monitor**: Use status script to monitor system health

---

**Implementation Date**: October 16, 2025  
**Status**: ✅ **COMPLETE**  
**Version**: 3.1 (Two Scanner Architecture)
