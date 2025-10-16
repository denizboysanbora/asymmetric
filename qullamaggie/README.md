# Qullamaggie Momentum Pattern Analyzer

> **"Listen to the market, not your opinions."** - Kristjan Kullamägi

A modular, production-quality momentum pattern analyzer inspired by Kristjan Kullamägi's trading style. Qullamaggie evaluates market gates, scans for high-momentum tight-flag setups with relative strength, and produces watchlists and dashboards - **analysis only, no trading**.

## 🎯 What Qullamaggie Does

1. **Market Gate Evaluation**: Analyzes QQQ's 10/20 EMA trend to determine if market conditions favor momentum plays
2. **Dynamic Universe Scanning**: Fetches liquid stocks from Alpaca API with filters for options, volume, and exchange
3. **Momentum Pattern Detection**: Identifies stocks with:
   - ADR ≥ 5% (Average Daily Range)
   - Relative Strength in top 90th percentile
   - Explosive legs ≥ 25% from swing low to high
   - Tight flag consolidations with higher lows
   - EP-style gap catalysts (when available)
4. **Opening Range Analysis**: Computes first 5-minute high/low and breakout triggers
5. **Email Notifications**: Sends ranked watchlists and breakout alerts

## 🚀 Quick Start

### 1. Setup

```bash
# Clone or navigate to qullamaggie directory
cd qullamaggie

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

Edit `.env` file (or `config/api_keys.env`):
```bash
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_SECRET_KEY=your_alpaca_secret_key_here
```

Get free API keys at: https://alpaca.markets/

### 3. Run Analysis

```bash
# Pre-market analysis (run before 9:30 AM ET)
python -m qullamaggie.run analyze

# Opening range analysis (run after 9:35 AM ET)
python -m qullamaggie.run opening-range

# Generate latest report
python -m qullamaggie.run report
```

## 📊 Usage Examples

### Pre-Market Analysis
```bash
python -m qullamaggie.run analyze --log-level DEBUG
```

**Output:**
```
================================================================================
🚀 QULLAMAGGIE MOMENTUM ANALYZER
================================================================================
Analysis Time: 2024-01-15 08:45:32 ET

📊 MARKET GATE (QQQ)
----------------------------------------
Gate Status: 🟢 OPEN
QQQ Close: $445.23
EMA 10: $443.15 (↗)
EMA 20: $441.87 (↗)

🎯 MOMENTUM CANDIDATES
----------------------------------------
Rank Symbol   RS     ADR    Flag EP   Price    Notes
1    NVDA     0.95   8.2%   ✓   🚀   $485.50  EP gap 6.1%
2    TSLA     0.93   7.8%   ✓        $245.30  
3    ROKU     0.91   6.5%   ✓        $89.45   
...
Total candidates: 12
EP gaps: 3 (25.0%)
Avg ADR: 6.8% | Avg RS: 0.92
```

### Opening Range Analysis
```bash
python -m qullamaggie.run opening-range
```

**Output:**
```
⚡ OPENING RANGE BREAKOUTS
----------------------------------------
Symbol  ORH      ORL      Last     Breakout
NVDA    $487.50  $484.20  $489.75  +0.46%
TSLA    $246.80  $244.10  $247.95  +0.47%

Breakout signals: 2/12 symbols
```

### Automated Scheduling

```bash
# Start automated mode (8 AM - 4 PM ET, weekdays)
./start.sh

# Check status
./status.sh

# Stop
./stop.sh
```

## ⚙️ Configuration

Edit `config.yaml` to customize:

```yaml
name: Qullamaggie
gate:
  proxy: QQQ
  ema_short: 10
  ema_long: 20
  rising_lookback: 3
scan:
  adr_min_pct: 5.0
  rs_top_percentile: 0.90
  explosive_leg_pct: 25.0
  flag:
    min_days: 5
    max_days: 20
    atr_contract_ratio: 0.7
    require_higher_lows: true
universe:
  mode: dynamic  # or 'static'
  min_price: 10.0
  min_avg_volume: 100000
  require_options: true
  exchanges: ["NYSE", "NASDAQ"]
```

## 📁 Output Files

Artifacts are saved to `artifacts/YYYY-MM-DD/`:

- **`gate.json`**: Market gate state and QQQ EMA metadata
- **`watchlist.csv`**: Ranked candidates with momentum characteristics
- **`candidates.json`**: Full candidate data with all metadata
- **`opening_range.csv`**: ORH/ORL and breakout triggers
- **`README.md`**: Field descriptions for all files

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test modules
pytest tests/test_features.py
pytest tests/test_opening_range.py

# Run with coverage
pytest --cov=qullamaggie tests/
```

## 📧 Email Integration

Qullamaggie sends email notifications via the existing Gmail integration:

- **Pre-market**: Watchlist with top candidates
- **Post-open**: Opening range breakout alerts

Recipients and email settings are configured in `output/gmail/`.

## 🔧 Command Reference

### CLI Commands

```bash
# Analyze market and screen candidates
python -m qullamaggie.run analyze [OPTIONS]
  --config PATH          Path to config.yaml file
  --log-level LEVEL      Logging level (DEBUG, INFO, WARNING, ERROR)
  --save/--no-save       Save artifacts to files

# Compute opening range breakouts
python -m qullamaggie.run opening-range [OPTIONS]
  --config PATH          Path to config.yaml file
  --log-level LEVEL      Logging level
  --save/--no-save       Save artifacts to files

# Generate latest report
python -m qullamaggie.run report [OPTIONS]
  --config PATH          Path to config.yaml file
  --log-level LEVEL      Logging level

# Create sample configuration
python -m qullamaggie.run create-config --output config.yaml
```

### Shell Scripts

```bash
./start.sh          # Start automated mode
./stop.sh           # Stop automated mode  
./status.sh         # Check status and logs
./qullamaggie.sh    # Manual execution
```

## 🏗️ Architecture

```
qullamaggie/
├── qullamaggie/           # Python package
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── data.py            # Alpaca API data fetching
│   ├── features.py        # Technical analysis functions
│   ├── screen.py          # Stock screening logic
│   ├── opening_range.py   # Opening range analysis
│   ├── report.py          # Output and dashboard
│   └── run.py             # CLI interface
├── tests/                 # Unit tests
├── artifacts/             # Output files
├── config/                # API keys and configuration
├── output/gmail/          # Email integration
├── config.yaml           # Main configuration
├── requirements.txt      # Python dependencies
└── *.sh                  # Shell scripts
```

## 🔍 Key Features

### Market Gate
- Evaluates QQQ 10/20 EMA trend
- Both EMAs must be rising over 3-day lookback
- EMA 10 must be above EMA 20

### Dynamic Universe
- Fetches liquid stocks from Alpaca API
- Filters: US equity, active, tradable, has options
- Excludes ETFs and leveraged products
- NYSE/NASDAQ only, 30% margin requirement

### Momentum Screening
- **ADR**: Average Daily Range ≥ 5%
- **RS Score**: Blend of 1/3/6-month return percentiles ≥ 90th
- **Explosive Leg**: ≥ 25% impulse from swing low to high
- **Tight Flag**: ATR contraction ≤ 70% with higher lows
- **EP Gap**: Premarket gap ≥ 4% (when available)

### Opening Range
- First 5-minute high/low calculation
- Breakout trigger: price > ORH
- Time validation and error handling

## 🚨 Important Notes

- **NO TRADING**: This is analysis only - no orders are placed
- **Market Hours**: Designed for 8 AM - 4 PM ET, weekdays
- **Data Requirements**: Requires Alpaca Market Data API access
- **Email Only**: No Twitter/X integration (removed from analyst)

## 🐛 Troubleshooting

### Common Issues

1. **Missing API Keys**
   ```
   ValueError: Missing Alpaca API credentials
   ```
   Solution: Set `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` in `.env`

2. **No Candidates Found**
   - Check market gate status (QQQ EMAs)
   - Verify universe has liquid stocks
   - Adjust screening criteria in `config.yaml`

3. **Opening Range Errors**
   - Ensure market is open (9:30 AM ET+)
   - Check for sufficient intraday data
   - Verify timezone settings

### Debug Mode
```bash
python -m qullamaggie.run analyze --log-level DEBUG
```

## 📈 Human-Simple Summary

**Qullamaggie doesn't trade; it analyzes.** 

It checks whether QQQ's 10/20-day EMAs are rising (market healthy). If healthy, it scans your tickers for fast leaders with tight flags and (ideally) a gap catalyst. After the bell, it marks the first 5-minute high/low and tells you which symbols would have triggered above that high. It saves a ranked watchlist and opening-range report for you — still no orders placed.

Perfect for momentum traders who want systematic pattern recognition without the complexity of automated trading systems.

## 📄 License

This project is for educational and analysis purposes. Use at your own risk.

---

*Built with Python, Alpaca API, and the wisdom of Kristjan Kullamägi's momentum trading principles.*
