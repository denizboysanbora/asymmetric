# X Auto-Tweet - Crypto Signals

Auto-tweets when crypto moves >2% daily, with volatility metrics.

## 🛡️ Rate Limiting

**All tweet posting is now protected from 429 errors!**

Check rate limit status:
```bash
./check_rate_limits.sh
```

See [RATE_LIMIT_QUICK_REF.md](../RATE_LIMIT_QUICK_REF.md) for quick reference or [docs/RATE_LIMITING.md](RATE_LIMITING.md) for full documentation.

## Setup

1. Ensure `config/.env` contains valid Twitter OAuth 1.0a keys:
   - `X_API_KEY`, `X_API_KEY_SECRET`
   - `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET`

## Usage

**Tweet now (check for >2% moves):**
```bash
./tweet_crypto.sh
```

**Run automatically (checks every 5 min):**
```bash
./venv/bin/python scripts/auto_tweet_crypto.py
```

## What gets tweeted

When crypto moves >2%, tweets like:

```
$ETH $4,109 +7.54% (RV=0.56, Z=-0.18, TR/ATR=0.21)
```

Each coin gets its own tweet (separate tweets for BTC, ETH, SOL, etc.)

## Configure

`crypto.yaml`:
- `threshold_pct: 2.0` - Daily move threshold
- `cooldown_minutes: 60` - Don't re-tweet same coin for 60 min

## Manual tweet

```bash
./venv/bin/python scripts/post_text_oauth1.py "Hello X!"
```


### Hourly Volatility Tweet — Parameters & Format

```
# Hourly Volatility Tweet — Parameters & Format
# Copy/paste into README or code comments.

# 1) Output line format (exact)
# ------------------------------------------------------------
# $<SYMBOL> $<PRICE> <CHANGE>% (RV=<RV_RATIO>, Z=<Z_SCORE>, TR/ATR=<TR_ATR>)
#
# Example:
# $SOL $193.60 +2.33% (RV=2.1, Z=3.2, TR/ATR=2.7)

# 2) Field definitions
# ------------------------------------------------------------
# SYMBOL     : Asset ticker, prefixed with '$' (e.g., $BTC, $ETH).
# PRICE      : Latest trade price at compute time.
# CHANGE%    : 24h percentage change.
#              Formula: ((price_now / price_24h_ago) - 1) * 100
# RV_RATIO   : Realized volatility ratio = σ_short / σ_long.
#              Typical windows: σ_short = std of 5m log-returns over last 1h (12 bars)
#                               σ_long  = std of 5m log-returns over last 7d (~20160 bars)
#              Fallback: if 7d not available, use 24h baseline (~288 bars).
# Z_SCORE    : Return z-score for current bar.
#              ret_t  = log(close_t) - log(close_{t-1})
#              z_t    = (ret_t - mean(ret_{t-N..t-1})) / std(ret_{t-N..t-1})
#              Typical N = 60 bars (~5 hours on 5m bars).
# TR/ATR     : True Range normalized by ATR(14, EMA).
#              TR_t   = max( high_t - low_t,
#                            |high_t - close_{t-1}|,
#                            |low_t  - close_{t-1}| )
#              ATR_t  = EMA(TR, span=14)
#              TR/ATR = TR_t / ATR_t

# 3) Interpretation (institutional thresholds)
# ------------------------------------------------------------
# RV_RATIO > 2.0  → volatility regime expansion (short-term vol >> long-term vol)
# |Z_SCORE| > 2.0 → statistically abnormal move (breakout confirmation)
# TR/ATR   > 2.0  → current bar is unusually large (event-driven spike)
# All three elevated → “Holy Trinity” breakout alignment.

# 4) Formatting rules
# ------------------------------------------------------------
# - No emojis.
# - PRICE: 2 decimals if price >= 1; use more (e.g., 6–8) for small-priced assets.
# - CHANGE%: always show sign and 2 decimals (e.g., +1.55% or -0.42%).
# - Metrics (RV, Z, TR/ATR): 2 decimals.
# - One asset per line; join multiple lines with '\n'.
# - Keep final tweet <= 280 chars; if needed, limit to top N assets by RV * |Z|.

# 5) Example block (multiple assets)
# ------------------------------------------------------------
# $SOL $193.60 +2.33% (RV=2.10, Z=3.20, TR/ATR=2.70)
# $DOGE $0.210000 +2.30% (RV=1.90, Z=3.00, TR/ATR=2.50)
# $AVAX $22.61 +1.26% (RV=1.60, Z=2.10, TR/ATR=1.90)
# $ETH $4,078.00 +1.00% (RV=1.50, Z=1.90, TR/ATR=1.80)
# $BTC $113,953.00 +0.62% (RV=1.40, Z=1.50, TR/ATR=1.60)

# 6) Frequency
# ------------------------------------------------------------
# - Compute and post hourly (top of the hour, UTC).
```
