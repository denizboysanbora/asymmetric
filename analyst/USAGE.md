# Investor Agent Usage Guide

## Quick Start

### 1. Email & Social Media Setup

```bash
# Gmail setup (if not already done)
cd /Users/deniz/Code/asymmetric/output/gmail/scripts
python3 gmail_auth.py

# Twitter/X rate limit check
cd /Users/deniz/Code/asymmetric/output/x/scripts
python3 rate_limit_status.py
```

### 2. Using the Web Interface

Use the investor commands to scan, email, and tweet signals.

Type commands in the chat interface:
- `scan AAPL` - Scan Apple stock
- `scan TSLA` - Scan Tesla stock
- `scan NVDA` - Scan Nvidia stock
- `email SYMBOL` - Email a signal
- `tweet SYMBOL` - Tweet a signal

## Command Reference

### Scan Command

Analyzes a stock symbol and returns real-time market data with technical indicators.

**Syntax**: `scan SYMBOL`

**Example**:
```bash
scan AAPL
```

**Response Format**:
```
$AAPL $247.54 +0.93% | 1.00x ATR | Z -0.42
```

**Breakdown**:
- `$AAPL` - Stock symbol
- `$247.54` - Current price
- `+0.93%` - 24-hour price change
- `1.00x ATR` - True Range / Average True Range ratio
- `Z -0.42` - Z-score (volatility measure)

### Email Command

Sends an email alert with the scan results.

**Syntax**: `email SYMBOL`

**Example**:
```bash
email AVGO
```

**Requirements**:
- Gmail API credentials configured in `output/gmail/config/`
- Gmail script must be authorized

### Tweet Command

Posts a tweet with the scan results.

**Syntax**: `tweet SYMBOL`

**Example**:
```bash
tweet TSLA
```

**Requirements**:
- X/Twitter API credentials configured
- Rate limit: 17 tweets per 24 hours

## API Usage

### Using curl

```bash
# Basic scan
curl -X POST http://localhost:3000/api/investor \
  -H "Content-Type: application/json" \
  -d '{"command":"scan AAPL"}'

# Pretty-printed with jq
curl -X POST http://localhost:3000/api/investor \
  -H "Content-Type: application/json" \
  -d '{"command":"scan TSLA"}' | jq .
```

### Using fetch (JavaScript)

```javascript
const response = await fetch('http://localhost:3000/api/investor', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    command: 'scan AAPL'
  })
});

const result = await response.json();
console.log(result);
// { success: true, output: "$AAPL $247.54 +0.93% | 1.00x ATR | Z -0.42", error: null }
```

### Using Python

```python
import requests

response = requests.post(
    'http://localhost:3000/api/investor',
    json={'command': 'scan NVDA'}
)

result = response.json()
print(result)
# {'success': True, 'output': '$NVDA $188.31 +2.81% | 0.64x ATR | Z -0.38', 'error': None}
```

## Direct Script Usage

### Using Python directly

```bash
cd /Users/deniz/Code/asymmetric
python3 execute_command.py "scan AAPL"
```

### Using shell scripts

```bash
cd /Users/deniz/Code/asymmetric/analyst/alpaca/alpaca-mcp-server

# Scan only
./scan.sh AAPL

# Email the result
./email.sh AVGO

# Tweet the result
./tweet.sh TSLA
```

## Rate Limiting

### API Rate Limits
- **API Endpoint**: 10 requests per minute per IP
- **Response**: 429 status code when limit exceeded

### Twitter Rate Limits
- **Tweets**: 17 tweets per 24 hours
- Managed by `output/x/scripts/tweet_with_limit.py`

## Error Handling

### Common Errors

**Invalid Symbol**:
```json
{
  "success": false,
  "output": null,
  "error": "Invalid command. Use: scan/email/tweet SYMBOL"
}
```

**Market Closed / No Data**:
```json
{
  "success": false,
  "output": null,
  "error": "No data available for symbol"
}
```

**Rate Limit**:
```json
{
  "success": false,
  "output": null,
  "error": "Rate limit exceeded. Max 10 requests per minute."
}
```

**Twitter Rate Limit**:
```json
{
  "success": false,
  "output": null,
  "error": "🚫 Rate limit reached (17 tweets/24h)"
}
```

## Technical Details

### Market Data Source
- **Provider**: Alpaca Markets API
- **Data**: Real-time market data (15-minute delay on free tier)
- **Update Frequency**: 5-minute bars for intraday analysis

### Technical Indicators

**True Range (TR)**:
- Measures price volatility
- Calculated as: max(high-low, |high-prev_close|, |low-prev_close|)

**Average True Range (ATR)**:
- Exponential moving average of True Range
- Period: 14 bars (EMA with alpha = 2/15)

**TR/ATR Ratio**:
- Current volatility vs. average volatility
- Values > 1.0 indicate elevated volatility

**Z-Score**:
- Measures how many standard deviations the latest return is from the mean
- Positive = above average, Negative = below average

### Signal Classification

The scanner uses `classify_long_entry()` from `compute_spike_params_stocks.py` to determine signal strength based on:
- TR/ATR ratio thresholds
- Z-score thresholds
- 24-hour price change percentage

## Troubleshooting

### Gmail authentication issues

```bash
cd /Users/deniz/Code/asymmetric/output/gmail/scripts
python3 gmail_auth.py  # Re-run OAuth flow
```

### Python venv issues

```bash
# Verify Python works
python3 --version

# Check installed packages
python3 -m pip list
```

### Alpaca API issues

```bash
# Check .env file exists and has keys
cat /Users/deniz/Code/asymmetric/analyst/alpaca/alpaca-mcp-server/.env

# Should contain:
# ALPACA_API_KEY=...
# ALPACA_SECRET_KEY=...
```

## Environment Configuration

### Required Files

1. **Alpaca credentials**: `analyst/alpaca/alpaca-mcp-server/.env`
2. **Gmail credentials**: `output/gmail/config/token.json` (optional, for email)
3. **Twitter credentials**: `output/x/config/` (optional, for tweets)

### Verifying Setup

Run this comprehensive test:

```bash
# Test 1: Direct Python entry
cd /Users/deniz/Code/asymmetric
python3 execute_command.py "scan AAPL"

# Test 2: Shell script
cd /Users/deniz/Code/asymmetric/analyst/alpaca/alpaca-mcp-server
./scan.sh TSLA

# Test 3: Twitter/X rate limits
cd /Users/deniz/Code/asymmetric/output/x/scripts
python3 rate_limit_status.py
```

All three should return successful scan results.

## Need Help?

Check the setup documentation in `SETUP_FIXES.md` for recent changes and fixes.

## BTC Snapshot Email Test

To send yourself a live BTC snapshot email (requires `output/gmail/config/token.json`):

```bash
```

