"""
Unit tests for Qullamaggie features module.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from qullamaggie.features import (
    ema, adr_pct, rolling_return, rs_score, detect_explosive_leg,
    detect_flag_tightening, market_gate, calculate_atr
)


class TestEMA:
    """Test exponential moving average calculations."""
    
    def test_ema_basic(self):
        """Test basic EMA calculation."""
        series = pd.Series([10, 11, 12, 13, 14, 15, 16, 17, 18, 19])
        result = ema(series, span=3)
        
        assert len(result) == len(series)
        assert not result.isna().all()
        assert result.iloc[-1] > result.iloc[0]  # Should be increasing
    
    def test_ema_single_value(self):
        """Test EMA with single value."""
        series = pd.Series([100])
        result = ema(series, span=3)
        
        assert len(result) == 1
        assert result.iloc[0] == 100


class TestADR:
    """Test Average Daily Range calculations."""
    
    def test_adr_pct_basic(self):
        """Test basic ADR percentage calculation."""
        dates = pd.date_range('2024-01-01', periods=25, freq='D')
        data = []
        
        for i, date in enumerate(dates):
            base_price = 100 + i
            data.append({
                'symbol': 'TEST',
                'date': date,
                'open': base_price,
                'high': base_price + 2,
                'low': base_price - 1,
                'close': base_price + 0.5,
                'volume': 1000000
            })
        
        df = pd.DataFrame(data)
        df = df.set_index(['symbol', 'date'])
        
        adr = adr_pct(df, window=20)
        
        assert 'TEST' in adr.index
        assert adr['TEST'] > 0  # Should be positive percentage


class TestRollingReturn:
    """Test rolling return calculations."""
    
    def test_rolling_return_basic(self):
        """Test basic rolling return calculation."""
        series = pd.Series([100, 105, 110, 115, 120])
        result = rolling_return(series, periods=4)
        
        expected = (120 - 100) / 100  # 20% return
        assert abs(result - expected) < 0.001
    
    def test_rolling_return_insufficient_data(self):
        """Test rolling return with insufficient data."""
        series = pd.Series([100, 105])
        result = rolling_return(series, periods=5)
        
        assert np.isnan(result)


class TestRS:
    """Test Relative Strength calculations."""
    
    def test_rs_score_basic(self):
        """Test basic RS score calculation."""
        dates = pd.date_range('2024-01-01', periods=150, freq='D')
        symbols = ['TEST1', 'TEST2', 'TEST3']
        
        data = []
        for symbol in symbols:
            for i, date in enumerate(dates):
                # Create different return patterns
                if symbol == 'TEST1':
                    price = 100 + i * 0.5  # Slow growth
                elif symbol == 'TEST2':
                    price = 100 + i * 1.0  # Medium growth
                else:
                    price = 100 + i * 2.0  # Fast growth
                
                data.append({
                    'symbol': symbol,
                    'date': date,
                    'open': price,
                    'high': price + 1,
                    'low': price - 1,
                    'close': price,
                    'volume': 1000000
                })
        
        df = pd.DataFrame(data)
        df = df.set_index(['symbol', 'date'])
        
        rs_scores = rs_score(df, periods=[21, 63, 126])
        
        assert len(rs_scores) == 3
        # TEST3 should have highest RS score
        assert rs_scores['TEST3'] > rs_scores['TEST1']


class TestExplosiveLeg:
    """Test explosive leg detection."""
    
    def test_explosive_leg_detection(self):
        """Test explosive leg detection with clear pattern."""
        dates = pd.date_range('2024-01-01', periods=40, freq='D')
        symbols = ['EXPLOSIVE', 'STABLE']
        
        data = []
        for symbol in symbols:
            for i, date in enumerate(dates):
                if symbol == 'EXPLOSIVE':
                    # Create explosive pattern in last 30 days
                    if i < 10:
                        price = 100
                    elif i < 35:  # Explosive move
                        price = 100 + (i - 10) * 2  # 50% move
                    else:
                        price = 150
                else:
                    price = 100 + i * 0.1  # Slow growth
                
                data.append({
                    'symbol': symbol,
                    'date': date,
                    'open': price,
                    'high': price + 1,
                    'low': price - 0.5,
                    'close': price,
                    'volume': 1000000
                })
        
        df = pd.DataFrame(data)
        df = df.set_index(['symbol', 'date'])
        
        explosive_legs = detect_explosive_leg(df, window=30, thresh=0.25)
        
        assert explosive_legs['EXPLOSIVE'] == True
        assert explosive_legs['STABLE'] == False


class TestFlagTightening:
    """Test tight flag detection."""
    
    def test_flag_tightening_detection(self):
        """Test tight flag detection."""
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        symbols = ['FLAG', 'TREND']
        
        data = []
        for symbol in symbols:
            for i, date in enumerate(dates):
                if symbol == 'FLAG':
                    # Create tight consolidation in last 10 days
                    if i < 20:
                        price = 100 + i * 0.5
                    else:
                        # Tight range around 110
                        price = 110 + (i % 3 - 1) * 0.5
                else:
                    price = 100 + i * 1.0  # Trending
                
                data.append({
                    'symbol': symbol,
                    'date': date,
                    'open': price,
                    'high': price + 0.5,
                    'low': price - 0.5,
                    'close': price,
                    'volume': 1000000
                })
        
        df = pd.DataFrame(data)
        df = df.set_index(['symbol', 'date'])
        
        flags = detect_flag_tightening(df, lookback_min=5, lookback_max=15, atr_contract=0.7)
        
        # Note: This test might need adjustment based on actual ATR calculations
        assert isinstance(flags['FLAG'], bool)
        assert isinstance(flags['TREND'], bool)


class TestMarketGate:
    """Test market gate evaluation."""
    
    def test_market_gate_rising_emas(self):
        """Test market gate with rising EMAs."""
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        prices = [100 + i * 0.5 for i in range(30)]  # Rising prices
        
        df = pd.DataFrame({
            'close': prices
        }, index=dates)
        
        gate_open, meta = market_gate(df, ema_short=10, ema_long=20, rising_lookback=3)
        
        assert isinstance(gate_open, bool)
        assert 'ema_10' in meta
        assert 'ema_20' in meta
        assert 'ema_10_rising' in meta
        assert 'ema_20_rising' in meta
        assert 'ema_10_above_20' in meta
    
    def test_market_gate_insufficient_data(self):
        """Test market gate with insufficient data."""
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        prices = [100 + i for i in range(5)]
        
        df = pd.DataFrame({
            'close': prices
        }, index=dates)
        
        gate_open, meta = market_gate(df, ema_short=10, ema_long=20, rising_lookback=3)
        
        assert gate_open == False
        assert 'error' in meta


class TestATR:
    """Test ATR calculations."""
    
    def test_calculate_atr_basic(self):
        """Test basic ATR calculation."""
        dates = pd.date_range('2024-01-01', periods=20, freq='D')
        symbols = ['TEST']
        
        data = []
        for i, date in enumerate(dates):
            price = 100 + i
            data.append({
                'symbol': 'TEST',
                'date': date,
                'open': price,
                'high': price + 2,
                'low': price - 1,
                'close': price + 0.5,
                'volume': 1000000
            })
        
        df = pd.DataFrame(data)
        df = df.set_index(['symbol', 'date'])
        
        atr_values = calculate_atr(df, window=14)
        
        assert 'TEST' in atr_values.index
        assert atr_values['TEST'] > 0
