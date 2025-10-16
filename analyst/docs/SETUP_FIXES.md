# Investor Agent Setup Fixes

## Date: October 13, 2025

## Issues Identified and Fixed

### 1. Path Configuration Issues

**Problem**: All scripts were referencing a non-existent `asymmetric` folder instead of the correct `box/investor` path structure.

**Files Fixed**:
- ✅ `/box/investor/execute_command.py` - Fixed BASE_DIR calculation (changed `parents[1]` to `parent`)
- ✅ `/box/investor/alpaca/alpaca-mcp-server/scan.py` - Updated gmail and x directory paths
- ✅ `/box/investor/alpaca/alpaca-mcp-server/email.sh` - Updated GMAIL_DIR path
- ✅ `/box/investor/alpaca/alpaca-mcp-server/tweet.sh` - Updated X_DIR path
- ✅ `/box/box/src/app/api/investor/route.ts` - Updated Python path candidates
- ✅ `/box/investor/README.md` - Updated documentation

### 2. Virtual Environment Path Issues

**Problem**: All three Python virtual environments (alpaca, gmail, x) had shebangs and pyvenv.cfg files pointing to the old `asymmetric` path.

**Fixed venvs**:
- ✅ `/box/investor/alpaca/alpaca-mcp-server/venv/` - Fixed pip shebangs and pyvenv.cfg
- ✅ `/box/investor/gmail/venv/` - Fixed pip shebangs and pyvenv.cfg
- ✅ `/box/investor/x/venv/` - Fixed pip shebangs and pyvenv.cfg

## Verification Tests Performed

### API Tests (via Next.js)
```bash
# Test 1: Scan AAPL
curl -X POST http://localhost:3000/api/investor \
  -H "Content-Type: application/json" \
  -d '{"command":"scan AAPL"}' | jq .
# ✅ Result: {"success":true,"output":"$AAPL $247.54 +0.93% | 1.00x ATR | Z -0.42","error":null}

# Test 2: Scan TSLA
curl -X POST http://localhost:3000/api/investor \
  -H "Content-Type: application/json" \
  -d '{"command":"scan TSLA"}' | jq .
# ✅ Result: {"success":true,"output":"$TSLA $435.89 +5.42% | 0.80x ATR | Z -0.01","error":null}

# Test 3: Scan NVDA
curl -X POST http://localhost:3000/api/investor \
  -H "Content-Type: application/json" \
  -d '{"command":"scan NVDA"}' | jq .
# ✅ Result: {"success":true,"output":"$NVDA $188.31 +2.81% | 0.64x ATR | Z -0.38","error":null}
```

### Direct Script Tests
```bash
# Test 1: Direct Python execution
cd /Users/deniz/Library/CloudStorage/Dropbox/Bora/Code/box/investor
./alpaca/alpaca-mcp-server/venv/bin/python3 execute_command.py "scan META"
# ✅ Result: {"success": true, "output": "$META $715.54 +1.45% | 1.21x ATR | Z 0.89", "error": null}

# Test 2: Shell script wrapper
cd /Users/deniz/Library/CloudStorage/Dropbox/Bora/Code/box/investor/alpaca/alpaca-mcp-server
./scan.sh AAPL
# ✅ Result: $AAPL $247.54 +0.93% | 1.00x ATR | Z -0.42
```

### Pip Verification
```bash
# All three venvs have working pip now
/Users/deniz/Library/CloudStorage/Dropbox/Bora/Code/box/investor/alpaca/alpaca-mcp-server/venv/bin/pip --version
# ✅ pip 25.2 from ...alpaca-mcp-server/venv/lib/python3.14/site-packages/pip (python 3.14)

/Users/deniz/Library/CloudStorage/Dropbox/Bora/Code/box/investor/gmail/venv/bin/pip --version
# ✅ pip 25.2 from ...gmail/venv/lib/python3.14/site-packages/pip (python 3.14)

/Users/deniz/Library/CloudStorage/Dropbox/Bora/Code/box/investor/x/venv/bin/pip --version
# ✅ pip 25.2 from ...x/venv/lib/python3.14/site-packages/pip (python 3.14)
```

## Current Working Structure

```
/Users/deniz/Library/CloudStorage/Dropbox/Bora/Code/box/
├── box/                          # Next.js application
│   ├── src/
│   │   └── app/
│   │       ├── api/
│   │       │   └── investor/
│   │       │       └── route.ts  # API endpoint (FIXED)
│   │       └── investor/         # UI components (unchanged)
│   └── ...
└── investor/                     # Backend logic
    ├── execute_command.py        # Main command executor (FIXED)
    ├── README.md                 # Documentation (UPDATED)
    ├── alpaca/
    │   └── alpaca-mcp-server/
    │       ├── scan.py           # Market scanner (FIXED)
    │       ├── scan.sh           # Scan wrapper
    │       ├── email.sh          # Email wrapper (FIXED)
    │       ├── tweet.sh          # Tweet wrapper (FIXED)
    │       └── venv/             # Python venv (FIXED)
    ├── gmail/
    │   ├── scripts/
    │   │   └── send_email.py
    │   └── venv/                 # Python venv (FIXED)
    └── x/
        ├── scripts/
        │   └── tweet_with_limit.py
        └── venv/                 # Python venv (FIXED)
```

## Commands Available

The investor agent now supports three commands via the API:

1. **scan SYMBOL** - Scan a stock/crypto symbol and return real-time analysis
2. **email SYMBOL** - Send an email alert for a symbol (requires gmail setup)
3. **tweet SYMBOL** - Tweet about a symbol (requires X/Twitter setup)

## Environment Setup

### Required Environment Variables (already configured in .env)
- `ALPACA_API_KEY` - Alpaca API key
- `ALPACA_SECRET_KEY` - Alpaca secret key

### Optional Environment Variables (for API route)
- `INVESTOR_COMMAND_SCRIPT` - Path to execute_command.py (auto-detected)
- `INVESTOR_PYTHON_BIN` - Path to Python interpreter (auto-detected)

## Next.js Development Server

The Next.js app is running on `http://localhost:3000` with the following endpoints:

- **Main App**: http://localhost:3000
- **Investor Page**: http://localhost:3000/investor
- **Investor API**: http://localhost:3000/api/investor (POST)

## Dependencies

All required Python packages are installed in the respective venvs:

### Alpaca venv
- alpaca-py (0.42.2)
- mcp (1.17.0)
- numpy (2.3.3)
- pandas (2.3.3)
- python-dotenv

### Gmail venv
- google-auth-oauthlib
- google-auth-httplib2
- google-api-python-client

### X/Twitter venv
- tweepy
- python-dotenv

## Status: ✅ FULLY OPERATIONAL

All path issues have been resolved and the investor agent is now fully functional. The system can:
- ✅ Execute scan commands via API
- ✅ Execute scan commands via direct Python
- ✅ Execute scan commands via shell scripts
- ✅ Process real-time market data from Alpaca
- ✅ Return formatted signal outputs

Email and tweet functionality depends on proper configuration of gmail and X/Twitter credentials.

