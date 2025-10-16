# 🚀 Qullamaggie Enhanced Setup Detection

## Overview
Qullamaggie has been enhanced to detect and analyze **all three timeless momentum setups** inspired by Kristjan Kullamägi's trading methodology. The system now provides comprehensive setup detection, ranking, and reporting capabilities.

## 🎯 The Three Setups

### 1️⃣ Qullamaggie Breakout
**Pattern**: Prior impulse + tight flag consolidation
- **Impulse**: 30-100%+ move within last 1-3 months
- **Flag**: 5-40 days of tight consolidation with:
  - Higher swing lows
  - ATR contraction ≤ 70% of baseline
  - Price surfing rising 10/20-day EMAs
- **Requirements**: ADR ≥ 5%, RS in top decile
- **Trigger**: Price breaks above Opening Range High (ORH)

### 2️⃣ Qullamaggie Episodic Pivot
**Pattern**: Gap up on powerful catalyst
- **Gap**: ≥ 10% over prior close
- **Volume**: Premarket notional ≥ $2M OR first 10min volume ≥ 2x average
- **Context**: Prefers flat prior 3-6 months (not extended)
- **Requirements**: ADR ≥ 5%
- **Trigger**: Intraday price > ORH after Episodic Pivot gap

### 3️⃣ Qullamaggie Parabolic Long
**Pattern**: Oversold rubber-band rebound
- **Crash**: ≥ 50% drop in ≤ 7 days
- **Oversold**: Price ≥ 2× ATR below 10/20-day EMA band
- **Requirements**: ADR ≥ 10%
- **Trigger**: First green 5-min candle or ORH break post-collapse

## 🏗️ Architecture Changes

### New Modules
- **`setups.py`**: Core setup detection logic with `SetupTag` model
- **Enhanced `features.py`**: Added gap detection, volume spike analysis, impulse detection
- **Updated `screen.py`**: Now uses setup-based candidate building
- **Enhanced `report.py`**: Shows setup-specific information in dashboards

### Configuration Updates
- **`config.yaml`**: Added setup-specific parameters for each pattern
- **Setup priorities**: Episodic Pivot > Breakout > Parabolic Long > RS > ADR
- **Flexible thresholds**: Configurable for each setup type

### Data Models
```python
class SetupTag(BaseModel):
    setup: Literal["Breakout", "Episodic Pivot", "Parabolic Long"]
    triggered: bool
    score: float  # 0-1 strength score
    meta: Dict    # Setup-specific metadata

class Candidate(BaseModel):
    symbol: str
    adr_pct: float
    rs_score: float
    setups: List[SetupTag]  # Multiple setups per symbol
    notes: List[str]
    meta: Dict
```

## 📊 Enhanced Outputs

### Dashboard Display
```
Rank Symbol    RS    ADR%   Breakout EP      Parabolic Price    Notes
1    NVDA      0.95  8.2%   ✓        🚀      📉         $450.25  Setups: Breakout, Episodic Pivot
2    TSLA      0.89  12.1%  ✗        🚀                    $245.80  Setups: Episodic Pivot
3    AMD       0.87  6.8%   ✓                    📉         $128.45  Setups: Breakout
```

### Summary Statistics
- **Setup Distribution**: Count and percentage of each setup type
- **Priority Ranking**: EP > Breakout > Parabolic Long > RS > ADR
- **Metadata**: Impulse percentages, gap sizes, drawdown amounts

### CSV Exports
- **Setup Columns**: Lists detected setups and scores
- **Metadata**: Detailed setup-specific information
- **Ranking**: Priority-ordered candidates

## 🔧 Technical Features

### Setup Detection Logic
- **Vectorized Operations**: Efficient pandas-based calculations
- **Multi-Setup Support**: Symbols can have multiple setups
- **Robust Error Handling**: Graceful degradation on data issues
- **Configurable Parameters**: Easy tuning via config.yaml

### Ranking System
1. **Primary**: Setup type (EP = 3, Breakout = 2, Parabolic = 1)
2. **Secondary**: Relative Strength score
3. **Tertiary**: ADR percentage

### Integration Points
- **Opening Range**: Setup triggers update based on intraday action
- **Market Gate**: QQQ trend filter applies to all setups
- **Universe**: Dynamic stock selection via Alpaca API

## 🚀 Usage Examples

### Command Line
```bash
# Full analysis with all setups
qullamaggie analyze

# Opening range updates
qullamaggie opening-range

# Dashboard report
qullamaggie report
```

### Configuration
```yaml
setups:
  breakout:
    impulse_min_pct: 30
    lookback_impulse_days: 60
    flag_min_days: 5
    flag_max_days: 40
    atr_contract_ratio: 0.7
  ep:
    gap_min_pct: 10
    premkt_notional_min: 2000000
    require_big_volume_minutes: 10
    prefer_flat_prior_months: true
  parabolic_long:
    crash_min_pct: 50
    lookback_days: 7
    oversold_atr_multiple: 2.0
```

## 🎯 Benefits

### For Analysis
- **Comprehensive Coverage**: All major momentum patterns
- **Clear Categorization**: Setup-specific metadata and scoring
- **Priority Ranking**: Focus on highest-probability setups
- **Rich Context**: Detailed setup formation criteria

### For Decision Making
- **Setup Awareness**: Know which pattern is driving the move
- **Risk Assessment**: Setup-specific volatility and timing
- **Entry Timing**: Opening range integration for precise entries
- **Market Context**: QQQ gate for overall market health

### For Automation
- **Scheduled Analysis**: Cron-based setup detection
- **Email Alerts**: Setup-specific notifications
- **Data Persistence**: Historical setup tracking
- **Integration Ready**: Modular design for extensions

## 🔄 Workflow

1. **Market Gate Check**: QQQ trend validation
2. **Universe Screening**: Dynamic stock selection
3. **Setup Detection**: All three patterns analyzed
4. **Candidate Ranking**: Priority-based ordering
5. **Opening Range**: Intraday trigger validation
6. **Reporting**: Dashboard and artifact generation

## 🎉 Result

Qullamaggie now provides a **complete momentum analysis system** that identifies, ranks, and tracks the three timeless setups that drive the most explosive moves in the market. The system maintains the same production-quality standards while adding sophisticated pattern recognition capabilities.

**Analysis-only, never trades** - pure intelligence for better decision making! 🧠📈
