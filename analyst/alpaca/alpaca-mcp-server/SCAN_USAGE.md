# Scan Function - Manual Ticker Analysis

Quick commands to analyze specific tickers and optionally email/tweet the results.

**Uses the same logic and thresholds as the main Investor scanner** - when you update thresholds in `compute_spike_params_stocks.py`, scan automatically uses them.

## Commands

### 1. Scan (Display Only)
Shows ticker analysis in Investor format without sending anything.

```bash
cd /Users/deniz/Library/CloudStorage/Dropbox/Bora/Code/asymmetric/alpaca/alpaca-mcp-server
./scan.sh AVGO
./scan.sh AVGO TSLA NVDA
```

**Output:**
```
$AVGO $333.95 +2.87% | 1.72x ATR | Z -1.72 | —
```

### 2. Email
Analyzes ticker(s) and emails the result.

```bash
./email.sh AVGO
./email.sh AVGO TSLA
```

**What happens:**
- Analyzes the ticker(s)
- Sends email to deniz@bora.box
- Subject: "Signal"
- Body: The signal line (e.g., `$AVGO $333.95 +2.87% | 1.72x ATR | Z -1.72 | —`)

### 3. Tweet
Analyzes ticker(s) and tweets the result.

```bash
./tweet.sh AVGO
./tweet.sh TSLA NVDA
```

**What happens:**
- Analyzes the ticker(s)
- Tweets the signal line
- Rate limited to 17 tweets/24h

## Format

All three commands use the same Investor signal format:

**No signal:**
```
$SYMBOL $PRICE ±X.XX% | X.XXx ATR | Z ±X.XX
```

**With signal:**
```
$SYMBOL $PRICE ±X.XX% | X.XXx ATR | Z ±X.XX | Breakout
```

- **Breakout** = Long signal (meets all criteria)
- No indicator shown when criteria not met (cleaner display)

## Signal Criteria

For a ticker to show **Breakout** (all must pass):
- TR/ATR > 2.0
- |Z-score| > 2.0  
- |ΔP| > 2%
- Z-score and ΔP both positive (same direction)

## Examples

```bash
# Check AVGO
./scan.sh AVGO

# Email AVGO analysis
./email.sh AVGO

# Tweet multiple tickers
./tweet.sh TSLA NVDA META
```
