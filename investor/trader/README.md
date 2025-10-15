# 🤖 Investor - Automated Signal Monitor

**Status:** ✅ Active & Running

## What It Does

Investor monitors both crypto and stock markets every 5 minutes and:
1. **Detects signals** using technical filters (TR/ATR, RV, Z-score)
2. **Sends immediate emails** for crypto and stocks
3. **Tweets immediately** - each signal separately on X (Twitter)

## Configuration

**Schedule:** Every 5 minutes (via cron)  
**Email:** deniz@bora.box  
**Subject:** "Signal" (for both crypto and stocks)  
**Format:** `$SYMBOL $PRICE +X.XX% | X.XXx ATR | Z X.XX | Breakout`  
**Tweets:** Rate limited (max 17 tweets per 24h)  
**Note:** Each signal sent as separate email; tweets skipped if limit reached (emails always sent)  
**Price Format:** No cents for $1,000+, with cents for under $1,000

## Filters

### Crypto Signals
- ≥2.0% move
- TR/ATR ≥ 2.0
- |Z| ≥ 2.0
- ~25 major cryptos (dynamic API detection)

### Stock Signals
- ≥2.0% move
- TR/ATR ≥ 2.0
- |Z| ≥ 2.0
- ~2,960 symbols (dynamic API detection)
  - 2,957 ultra-liquid stocks (NYSE/NASDAQ, options, 30% margin)
  - 3 major ETFs (SPY, QQQ, GLD)
- **Excludes:** Other ETFs, leveraged products, illiquid stocks

## Example Output

**Crypto Signals (if triggered):**
- 📧 Immediate email to deniz@bora.box with subject "Signal" (one per signal)
- 🐦 Immediate separate tweet for each crypto signal
```
$BTC $67,450 +2.45% | 2.25x ATR | Z 2.24 | Breakout
$ETH $3,240 +2.78% | 2.38x ATR | Z 2.56 | Breakout
```

**Stock Signals (if triggered):**
- 📧 Immediate email to deniz@bora.box with subject "Signal" (one per signal)
- 🐦 Immediate separate tweet for each stock signal
```
$NVDA $183.15 +2.52% | 2.18x ATR | Z 2.45 | Breakout
$AMD $142.34 +2.85% | 2.32x ATR | Z 2.67 | Breakout
```

## Files

- **Script:** `trader/investor.sh` (orchestrates everything)
- **Crypto Scanner:** `alpaca/alpaca-mcp-server/compute_spike_params.py`
- **Stock Scanner:** `alpaca/alpaca-mcp-server/compute_spike_params_stocks.py`
- **Log:** `trader/logs/investor.log`
- **Cron:** Runs every 5 minutes (*/5 * * * *) ✅ ACTIVE

## Manual Testing

Run manually anytime from repo root:
```bash
bash asymmetric/trader/investor.sh
```

## View Logs

```bash
tail -f asymmetric/trader/logs/investor.log
```

## Cron Schedule

View current schedule:
```bash
crontab -l
```

Edit schedule:
```bash
crontab -e
```

## How It Works

1. **Every 5 minutes:** Cron triggers investor.sh
2. **Crypto check:** Runs compute_spike_params.py (~25 major cryptos)
3. **Stock check:** Runs compute_spike_params_stocks.py (~2,960 symbols: 2,957 stocks + SPY/QQQ/GLD)
4. **If crypto signals found:**
   - Send immediate email with all crypto signals
   - Tweet each signal immediately
5. **If stock signals found:**
   - Send immediate email with all stock signals
   - Tweet each signal immediately
6. **Log results:** All activity logged to investor.log

## Why Immediate Alerts?

- **Real-time:** Get notified as soon as volatility spikes occur
- **Actionable:** Can respond to market moves quickly
- **No delays:** No waiting for hourly summaries

## Why Separate Emails?

- Easier to filter/organize in inbox
- Clear distinction between asset classes
- Can set up different inbox rules for each

## Why Separate Tweets?

- Each signal gets its own visibility
- Better engagement on X
- Easier to track individual signals
- No character limit issues

## Tweet Rate Limiting (17/24h)

- **Limit:** Maximum 17 tweets per rolling 24-hour window
- **Protection:** Prevents Twitter API rate limit violations
- **Fallback:** Emails always sent, even if tweets are skipped
- **Automatic:** Tracks and enforces limit automatically
- **Logging:** Clear messages when limit is reached

Check current status:
```bash
cd asymmetric/x
./venv/bin/python3 scripts/test_rate_limiter.py
```

See `x/TWEET_RATE_LIMITING.md` for full documentation.

## Status Check

Check if it's running:
```bash
ps aux | grep investor || echo "Not currently running (will run at next hour)"
```

Check last run:
```bash
tail -20 asymmetric/trader/logs/investor.log
```
