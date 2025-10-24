# Environment Loading and Fallback System Guide

## Overview

Your Alpaca trading system has a robust environment variable loading and fallback mechanism. This guide explains how it works and the improvements I've made.

## How It Works

### 1. Environment Variable Loading Flow

```
1. Check if ALPACA_API_KEY and ALPACA_SECRET_KEY are already in environment
2. If not found, load from analyst/config/api_keys.env using load_dotenv()
3. If still missing, fall back to static 79-symbol list
4. If keys present but network fails, also fall back to static list
```

### 2. Network Connectivity Checks

The system now includes comprehensive network diagnostics:
- DNS resolution test for `data.alpaca.markets`
- HTTPS connectivity test with 5-second timeout
- Graceful fallback when network access is blocked

### 3. Enhanced Logging

The system now provides detailed logging for:
- Environment variable state before and after loading
- Network connectivity status
- API client initialization success/failure
- Screener API call results
- Fallback triggers and reasons

## Files Modified

### `breakout_analysis.py`
- Enhanced `get_liquid_stocks()` function with detailed logging
- Added network connectivity diagnostics
- Improved error handling and user feedback
- Better fallback messaging

### `test_env_loading.py` (NEW)
- Comprehensive test suite for environment loading
- Network connectivity testing
- Function behavior verification
- Clear pass/fail reporting

## Usage

### Running the Test Suite

```bash
cd /Users/deniz/Code/asymmetric/analyst
python test_env_loading.py
```

This will test:
1. Environment variable loading from `.env` file
2. Network connectivity to Alpaca
3. The `get_liquid_stocks()` function behavior

### Expected Output

When network access is blocked (your current situation):
```
🔑 Initial env state: API_KEY=✗, SECRET_KEY=✗
📁 Loading API keys from /path/to/api_keys.env
🔑 Post-load env state: API_KEY=✓, SECRET_KEY=✓
🌐 DNS resolution: ✗ (data.alpaca.markets) - [Errno 8] nodename nor servname provided, or not known
⚠️  Network access blocked, using fallback list
✅ Using 79 liquid symbols from fallback list
```

## Configuration

### Environment Variables

The system respects these environment variables:
- `LIQUID_UNIVERSE_CACHE_MINUTES` (default: 20)
- `LIQUID_UNIVERSE_MOST_ACTIVE_TOP` (default: 200)
- `LIQUID_UNIVERSE_MOVERS_TOP` (default: 100)
- `LIQUID_UNIVERSE_MAX` (default: 500)
- `LIQUID_UNIVERSE_MIN_PRICE` (default: 5)
- `LIQUID_UNIVERSE_MAX_PRICE` (default: 500)
- `LIQUID_UNIVERSE_MIN_DAILY_VOLUME` (default: 500000)
- `LIQUID_UNIVERSE_DISABLE_CACHE` (disable caching)

### API Keys File

Your API keys are stored in `analyst/config/api_keys.env`:
```
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_key_here
```

## Troubleshooting

### Common Issues

1. **"No .env file found"**
   - Ensure `analyst/config/api_keys.env` exists
   - Check file permissions

2. **"DNS resolution failed"**
   - Network access is blocked (expected in your case)
   - System will automatically use fallback list

3. **"API keys missing after all attempts"**
   - Check `.env` file format (no spaces around `=`)
   - Verify file encoding (UTF-8)

### Debug Mode

To see detailed logging, run your scanner with stderr output:
```bash
python breakout_scanner.py 2>&1 | tee debug.log
```

## Fallback List

When API access fails, the system uses a curated list of 79 liquid stocks:
- Major tech stocks (AAPL, MSFT, GOOGL, etc.)
- Financial stocks (JPM, BAC, GS, etc.)
- Energy stocks (XOM, CVX, COP, etc.)
- Healthcare stocks (GILD, AMGN, JNJ, etc.)

## Benefits of This System

1. **Resilient**: Works even when network access is blocked
2. **Transparent**: Clear logging shows what's happening
3. **Configurable**: Easy to adjust parameters
4. **Cached**: Reduces API calls when possible
5. **Fallback**: Always provides a working stock universe

## Next Steps

1. Run the test suite to verify everything works
2. Monitor the enhanced logging output
3. Adjust configuration parameters as needed
4. Consider adding more sophisticated fallback strategies if needed

The system is now more robust and provides better visibility into its operation!
