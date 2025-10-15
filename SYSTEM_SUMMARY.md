# Automated Trading Bot v2.0 - System Summary

## 🎯 Overview

Comprehensive automated trading signal system that scans markets, tweets signals, sends email alerts, and logs everything to a database.

## 📅 Schedule

### Weekdays (Monday - Friday)
- **Asset**: Stocks
- **Hours**: 10:00 AM - 4:00 PM ET
- **Interval**: Every 25 minutes
- **Scans per day**: 14
- **Tweet limit**: 17/day (3 buffer remaining)

### Weekends (Saturday - Sunday)
- **Asset**: Cryptocurrency
- **Hours**: 24/7 (crypto markets never close)
- **Interval**: Every 25 minutes
- **Scans per day**: 57 (but we use best judgment for tweeting)

## 🔄 Workflow (Every 25 Minutes)

1. **Scan Market**
   - Weekdays: Scan all stocks for volatility
   - Weekends: Scan crypto (BTC, ETH, SOL, etc.)

2. **Select Best Signal**
   - If signals meet thresholds → Pick most volatile
   - If no signals meet thresholds → Pick best available
   - Ranking: Weighted score (TR/ATR × 0.4 + Z-Score × 0.4 + %Change × 0.2)

3. **Tweet Signal**
   - Post to Twitter/X
   - Rate-limited: 17 tweets/24h
   - Auto-queues if limit reached

4. **Email Signal**
   - Send to: deniz@bora.box
   - Subject: "Trading Signal - STOCK" or "Trading Signal - CRYPTO"

5. **Save to Database**
   - SQLite: `/Users/deniz/Code/asymmetric/database/signals.db`
   - Stores: timestamp, symbol, price, change%, TR/ATR, Z-score, signal type, asset class

## 📊 Signal Criteria

### Stock Thresholds (to get "| L" or "| S" designation)
- **TR/ATR** > 2.0 (volatility 2x above average)
- **Z-Score** > 2.0 (2 standard deviations)
- **24h Change** > 2% (significant move)

### Crypto Thresholds
- **TR/ATR** > 2.0
- **Z-Score** > 2.5
- **24h Change** > 3%

### Best Available Mode
If no signals meet thresholds:
- System still selects the highest ranked signal
- Ensures you don't miss important moves
- Tagged without "| L" or "| S"

## 📈 Tweet Format

```
$AAPL $247.54 +2.93% | 2.45x ATR | Z 3.27 | L
```

Components:
- `$SYMBOL` - Stock/crypto ticker
- `$PRICE` - Current price
- `±X.XX%` - 24-hour change
- `X.XXx ATR` - True Range / Average True Range
- `Z X.XX` - Z-score (volatility measure)
- `| L` or `| S` - Long or Short signal (if meets thresholds)

## 🗄️ Database Schema

Table: `signals`
```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    symbol TEXT,
    price REAL,
    change_pct REAL,
    tr_atr REAL,
    z_score REAL,
    signal_type TEXT,
    asset_class TEXT
);
```

## 📁 File Structure

```
/Users/deniz/Code/asymmetric/
├── alpaca/alpaca-mcp-server/
│   ├── auto_scan_tweet_v2.py       ← Main bot script
│   ├── compute_spike_params_stocks.py ← Stock scanner
│   ├── compute_spike_params.py      ← Crypto scanner
│   ├── check_market_open.py         ← Market hours checker
│   └── .env                         ← Alpaca API keys
├── x/
│   ├── scripts/tweet_with_limit.py  ← Tweet with rate limiting
│   └── config/.env                  ← Twitter API keys
├── gmail/
│   ├── scripts/send_email.py        ← Email sender
│   └── config/token.json            ← Gmail credentials
├── database/
│   ├── log_signal.py                ← Database logger
│   └── signals.db                   ← SQLite database
├── start_auto_trader.sh             ← Start bot
├── stop_auto_trader.sh              ← Stop bot
├── status.sh                        ← Check status
└── auto_scan_tweet.log              ← Live logs
```

## 🚀 Commands

### Start System
```bash
cd /Users/deniz/Code/asymmetric
./start_auto_trader.sh
```

### Check Status
```bash
./status.sh
```

### View Live Logs
```bash
tail -f /Users/deniz/Code/asymmetric/auto_scan_tweet.log
```

### Stop System
```bash
./stop_auto_trader.sh
```

## 📊 Expected Activity

### Typical Weekday
```
10:00 AM - First scan & tweet
10:25 AM - Tweet #2
10:50 AM - Tweet #3
...
03:35 PM - Tweet #14 (last one)
04:00 PM - Market closes, bot sleeps
```

### Typical Weekend Day
```
Scans every 25 minutes continuously
Tweets when significant crypto moves detected
Less activity than weekdays (crypto less volatile than stocks)
```

## 🔐 API Keys Configured

- ✅ Alpaca Markets (market data)
- ✅ Twitter/X (tweeting)
- ❓ Gmail (needs verification)

## 📧 Email Setup

Gmail integration requires:
1. OAuth2 credentials in `/Users/deniz/Code/asymmetric/gmail/config/token.json`
2. If not set up, emails will fail (but tweets and database will still work)

To set up Gmail:
```bash
cd /Users/deniz/Code/asymmetric/gmail/scripts
python3 gmail_auth.py
```

## 💾 Database Queries

View all signals:
```bash
cd /Users/deniz/Code/asymmetric/database
sqlite3 signals.db "SELECT * FROM signals ORDER BY timestamp DESC LIMIT 10;"
```

Count by asset class:
```bash
sqlite3 signals.db "SELECT asset_class, COUNT(*) FROM signals GROUP BY asset_class;"
```

Best signals of the day:
```bash
sqlite3 signals.db "SELECT * FROM signals WHERE date(timestamp) = date('now') ORDER BY tr_atr DESC;"
```

## 🎯 Current Status

- **System**: v2.0 Running (PID: 5601)
- **Mode**: Sleeping until Wednesday 10:00 AM ET
- **Next Action**: Scan stocks at market open
- **Tweet Limit**: 1/17 used (16 remaining)

## 🔧 Troubleshooting

### Bot not tweeting
```bash
cd /Users/deniz/Code/asymmetric/x
./check_rate_limits.sh
```

### Check if running
```bash
ps aux | grep auto_scan_tweet_v2.py
```

### Restart bot
```bash
./stop_auto_trader.sh
./start_auto_trader.sh
```

### View recent errors
```bash
tail -50 auto_scan_tweet.log | grep -i error
```

## 📈 Performance Metrics

- **Response Time**: ~60 seconds per scan cycle
- **API Calls**: ~14 per weekday (stocks), ~57 per weekend day (crypto)
- **Storage**: ~1KB per signal, ~365KB per year
- **Uptime**: Designed for 24/7 operation

## 🎯 Success Criteria

A successful day:
- ✅ 14 tweets sent (weekday) or appropriate amount (weekend)
- ✅ 14 emails sent
- ✅ 14 database entries
- ✅ No rate limit errors
- ✅ All scans complete within 60 seconds

## 📞 Support

System built: October 14, 2025
Version: 2.0
Status: Production Ready ✅

