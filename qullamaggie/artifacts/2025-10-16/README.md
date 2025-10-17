# Qullamaggie Analysis Artifacts

Generated on: 2025-10-16 20:56:20 ET

## Files

### gate.json
Market gate state and QQQ EMA metadata:
- `gate_open`: Boolean indicating if market gate is open
- `ema_10`, `ema_20`: Current EMA values
- `ema_10_slope`, `ema_20_slope`: EMA slopes over lookback period
- `rising_lookback`: Number of days checked for rising EMAs
- `ema_10_rising`, `ema_20_rising`: Boolean indicators for rising EMAs
- `ema_10_above_20`: Boolean indicating EMA ordering

## Analysis Summary

This analysis evaluates:
1. **Market Gate**: QQQ 10/20 EMA trend (both rising + EMA10 > EMA20)
2. **Momentum Scan**: ADR ≥5%, RS in top 90%, explosive leg ≥25%, tight flag pattern
3. **Gap Catalysts**: EP-style gaps ≥4% (when available)
4. **Opening Range**: First 5-minute high/low and breakout triggers

**Note**: This is analysis only - no trading orders are placed.
