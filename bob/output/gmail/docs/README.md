# Crypto Alerts

Emails you when crypto moves >2% daily, with volatility metrics included.

## Setup

1. Set your email in `alerts.yaml`:
   ```yaml
   recipient: "your-email@gmail.com"
   ```

2. Authenticate Gmail once:
   ```bash
   cd /Users/deniz/Library/CloudStorage/Dropbox/Bora/Code/asymmetric/gmail
   ./venv/bin/python scripts/gmail_auth.py
   ```

## Usage

**Check now:**
```bash
./check_crypto.sh
```

**Run automatically (checks every 5 min):**
```bash
./venv/bin/python scripts/simple_alert_runner.py
```

## What you get

```
Subject: Signal

$ETH $4,108 +7.51% (RV=0.58, Z=-0.23, TR/ATR=0.11)
$SOL $192.56 +5.39% (RV=0.52, Z=-0.38, TR/ATR=0.33)
$DOGE $0.207010 +7.64% (RV=0.14, Z=-0.35, TR/ATR=0.49)
```

**Metrics:**
- **RV** = Volatility ratio (σ_short 1h / σ_long 7d)
- **Z** = Statistical abnormality (std deviations)
- **TR/ATR** = Bar size vs average

## Configure

`alerts.yaml`:
- `threshold_pct: 2.0` - Daily move threshold (2% triggers alert)
- `cooldown_minutes: 60` - Don't re-alert same coin for 60 min
