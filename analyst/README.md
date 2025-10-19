# Unified Analyst - Breakout Detection System

A consolidated, powerful analyst system that combines all breakout detection functionality into a single, easy-to-use script.

## 🚀 Quick Start

### Basic Usage
```bash
# Run single scan
./analyst.sh scan breakout 30 10

# Start daemon mode
./analyst.sh start breakout true false false 30 10

# Check status
./analyst.sh status

# Stop analyst
./analyst.sh stop
```

### Direct Python Usage
```bash
# Single scan
python analyst.py --mode breakout --scan --max-stocks 30 --top-n 10

# Daemon mode with auto-trading
python analyst.py --mode breakout --daemon --auto-trade --max-stocks 50

# MCP integration
python analyst.py --mode mcp --scan --use-mcp --max-stocks 30
```

## 📊 Features

### **Unified Functionality**
- ✅ **Breakout Detection**: Flag and range breakout patterns
- ✅ **Advanced Filtering**: Comprehensive stock universe filtering
- ✅ **MCP Integration**: Model Context Protocol support
- ✅ **Auto-Trading**: Automated trade execution
- ✅ **Email Notifications**: Signal alerts via email
- ✅ **Portfolio Management**: Position tracking and risk management

### **Technical Indicators**
- RSI (Relative Strength Index)
- ATR (Average True Range)
- Z-Score (Momentum measure)
- ADR (Average Daily Range)
- Relative Strength vs SPY

### **Trading Features**
- Position sizing (10% of portfolio per position)
- Risk management (5% stop loss, 15% take profit)
- Portfolio state persistence
- Real-time market data via Alpaca API

## 🎯 Modes

### **Breakout Mode** (Default)
Detects flag and range breakout patterns using technical analysis.

### **Advanced Mode**
Uses comprehensive filtering including:
- Price filters (>$5, <$1000)
- Volume filters (>500K daily volume)
- ADR filters (>5% average daily range)
- Relative strength filters (>1.0 vs SPY)

### **MCP Mode**
Integrates with Model Context Protocol for enhanced AI-powered analysis.

## 📋 Commands

### Shell Script Commands
```bash
./analyst.sh start [mode] [daemon] [auto-trade] [use-mcp] [max-stocks] [top-n]
./analyst.sh stop
./analyst.sh status
./analyst.sh scan [mode] [max-stocks] [top-n]
./analyst.sh logs
./analyst.sh help
```

### Python Script Options
```bash
python analyst.py --mode {breakout,advanced,mcp}
python analyst.py --scan                    # Single scan
python analyst.py --daemon                  # Continuous monitoring
python analyst.py --auto-trade              # Enable auto-trading
python analyst.py --use-mcp                 # Enable MCP integration
python analyst.py --max-stocks N            # Limit stocks analyzed
python analyst.py --top-n N                 # Show top N signals
```

## ⚙️ Configuration

### **Operating Hours**
- Schedule: 10 AM - 4 PM Eastern Time (weekdays)
- Daemon mode: Runs every 30 minutes during market hours

### **Email Settings**
- Recipient: `deniz@bora.box`
- Subject: "Flag Breakout Signal"
- Format: Clean signal format with technical indicators

### **Trading Parameters**
- Max position size: 10% of portfolio
- Stop loss: 5%
- Take profit: 15%
- Starting capital: $100,000

## 📁 File Structure

```
analyst/
├── analyst.py              # Unified analyst script
├── analyst.sh              # Management shell script
├── config/
│   └── api_keys.env        # API credentials
├── input/alpaca/venv/      # Python virtual environment
├── logs/                   # Log files
└── portfolio_state.json    # Portfolio state persistence
```

## 🔧 Setup

### **1. Install Dependencies**
```bash
cd analyst/input/alpaca/venv
./bin/pip install numpy pandas pydantic python-dotenv alpaca-py
```

### **2. Configure API Keys**
```bash
# Edit config/api_keys.env
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
```

### **3. Test the System**
```bash
./analyst.sh scan breakout 5 3
```

## 📊 Output Format

### **Breakout Signals**
```
$SYMBOL $PRICE +X.X% | ## RSI | X.XXx ATR | Z X.X | Flag/Range Breakout
```

**Example:**
```
$NVDA $450.25 +2.3% | 65 RSI | 2.10x ATR | Z 1.8 | Flag Breakout
$TSLA $250.50 +1.7% | 58 RSI | 1.90x ATR | Z 1.2 | Range Breakout
```

### **Email Notifications**
- Clean signal format
- Technical indicators
- Timestamp
- Multiple signals per email

## 🚨 Monitoring

### **Check Status**
```bash
./analyst.sh status
```

### **View Logs**
```bash
./analyst.sh logs
# or
tail -f logs/analyst.log
```

### **Stop Analyst**
```bash
./analyst.sh stop
```

## 🔄 Migration from Old System

The unified analyst replaces all previous scripts:
- ❌ `breakout_analysis.py` → ✅ `analyst.py`
- ❌ `breakout_scanner.py` → ✅ `analyst.py`
- ❌ `advanced_scanner.py` → ✅ `analyst.py`
- ❌ `mcp_analyst.py` → ✅ `analyst.py`
- ❌ Multiple shell scripts → ✅ `analyst.sh`

## 📈 Performance

- **90% reduction** in file count
- **Single point of maintenance**
- **Consistent behavior** across all modes
- **Better performance** (no duplicate API calls)
- **Simplified deployment**

## 🛠️ Troubleshooting

### **Common Issues**

1. **Module not found errors**
   ```bash
   cd analyst/input/alpaca/venv
   ./bin/pip install -r ../../../requirements.txt
   ```

2. **API key errors**
   ```bash
   # Check config/api_keys.env exists and has valid keys
   cat config/api_keys.env
   ```

3. **Permission errors**
   ```bash
   chmod +x analyst.sh
   ```

### **Debug Mode**
```bash
# Run with verbose output
python analyst.py --mode breakout --scan --max-stocks 5 --top-n 3
```

## 📞 Support

- **Status**: `./analyst.sh status`
- **Logs**: `./analyst.sh logs`
- **Help**: `./analyst.sh help`

---

**Version**: 1.0 (Unified Analyst)  
**Status**: Production Ready ✅
