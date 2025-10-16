"""
Unit tests for Qullamaggie opening range module.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta

from qullamaggie.opening_range import (
    compute_opening_range, validate_opening_range_data,
    get_entry_signals, calculate_or_breakout_strength,
    summarize_opening_range_results
)


class TestOpeningRange:
    """Test opening range calculations."""
    
    def create_sample_intraday_data(self, symbol='TEST', breakout=False):
        """Create sample intraday data for testing."""
        start_time = datetime.now().replace(hour=9, minute=30, second=0, microsecond=0)
        timestamps = [start_time + timedelta(minutes=i) for i in range(10)]
        
        data = []
        for i, ts in enumerate(timestamps):
            base_price = 100 + i * 0.1
            
            if breakout and i >= 5:  # Breakout after 5 minutes
                base_price = 102 + i * 0.1
            
            data.append({
                'symbol': symbol,
                'timestamp': ts,
                'open': base_price,
                'high': base_price + 0.5,
                'low': base_price - 0.3,
                'close': base_price,
                'volume': 1000
            })
        
        df = pd.DataFrame(data)
        df = df.set_index(['symbol', 'timestamp'])
        return df
    
    def test_compute_opening_range_basic(self):
        """Test basic opening range computation."""
        minute_df = self.create_sample_intraday_data()
        
        results = compute_opening_range(minute_df, or_minutes=5)
        
        assert 'TEST' in results
        result = results['TEST']
        
        assert 'orh' in result
        assert 'orl' in result
        assert 'last_price' in result
        assert 'entry_triggered' in result
        
        assert result['orh'] > result['orl']  # High should be higher than low
        assert isinstance(result['entry_triggered'], bool)
    
    def test_compute_opening_range_breakout(self):
        """Test opening range with breakout."""
        minute_df = self.create_sample_intraday_data(breakout=True)
        
        results = compute_opening_range(minute_df, or_minutes=5)
        
        assert 'TEST' in results
        result = results['TEST']
        
        # Should detect breakout
        assert result['entry_triggered'] == True
        assert result['last_price'] > result['orh']
    
    def test_compute_opening_range_no_data(self):
        """Test opening range with no data."""
        empty_df = pd.DataFrame()
        
        results = compute_opening_range(empty_df, or_minutes=5)
        
        assert results == {}
    
    def test_compute_opening_range_insufficient_data(self):
        """Test opening range with insufficient data."""
        # Create data outside opening range hours
        start_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        timestamps = [start_time + timedelta(minutes=i) for i in range(5)]
        
        data = []
        for ts in timestamps:
            data.append({
                'symbol': 'TEST',
                'timestamp': ts,
                'open': 100,
                'high': 101,
                'low': 99,
                'close': 100,
                'volume': 1000
            })
        
        df = pd.DataFrame(data)
        df = df.set_index(['symbol', 'timestamp'])
        
        results = compute_opening_range(df, or_minutes=5)
        
        assert 'TEST' in results
        result = results['TEST']
        assert 'error' in result


class TestOpeningRangeValidation:
    """Test opening range data validation."""
    
    def test_validate_opening_range_data_valid(self):
        """Test validation with valid opening range data."""
        start_time = datetime.now().replace(hour=9, minute=30, second=0, microsecond=0)
        timestamps = [start_time + timedelta(minutes=i) for i in range(6)]
        
        data = []
        for ts in timestamps:
            data.append({
                'symbol': 'TEST',
                'timestamp': ts,
                'open': 100,
                'high': 101,
                'low': 99,
                'close': 100,
                'volume': 1000
            })
        
        df = pd.DataFrame(data)
        df = df.set_index(['symbol', 'timestamp'])
        
        validation_results = validate_opening_range_data(df, or_minutes=5)
        
        assert 'TEST' in validation_results
        assert validation_results['TEST'] == True
    
    def test_validate_opening_range_data_invalid(self):
        """Test validation with invalid opening range data."""
        # Create data with gaps
        start_time = datetime.now().replace(hour=9, minute=30, second=0, microsecond=0)
        timestamps = [start_time + timedelta(minutes=i*2) for i in range(3)]  # Every 2 minutes
        
        data = []
        for ts in timestamps:
            data.append({
                'symbol': 'TEST',
                'timestamp': ts,
                'open': 100,
                'high': 101,
                'low': 99,
                'close': 100,
                'volume': 1000
            })
        
        df = pd.DataFrame(data)
        df = df.set_index(['symbol', 'timestamp'])
        
        validation_results = validate_opening_range_data(df, or_minutes=5)
        
        assert 'TEST' in validation_results
        # Should be invalid due to gaps
        assert validation_results['TEST'] == False


class TestEntrySignals:
    """Test entry signal detection."""
    
    def test_get_entry_signals_basic(self):
        """Test basic entry signal detection."""
        opening_range_results = {
            'SYMBOL1': {
                'orh': 100,
                'orl': 99,
                'last_price': 101,
                'entry_triggered': True
            },
            'SYMBOL2': {
                'orh': 100,
                'orl': 99,
                'last_price': 99.5,
                'entry_triggered': False
            }
        }
        
        triggered = get_entry_signals(opening_range_results)
        
        assert 'SYMBOL1' in triggered
        assert 'SYMBOL2' not in triggered
    
    def test_get_entry_signals_empty(self):
        """Test entry signal detection with empty results."""
        opening_range_results = {}
        
        triggered = get_entry_signals(opening_range_results)
        
        assert triggered == []


class TestBreakoutStrength:
    """Test breakout strength calculations."""
    
    def test_calculate_or_breakout_strength(self):
        """Test breakout strength calculation."""
        opening_range_results = {
            'BREAKOUT': {
                'orh': 100,
                'last_price': 105,
                'entry_triggered': True
            },
            'NO_BREAKOUT': {
                'orh': 100,
                'last_price': 98,
                'entry_triggered': False
            }
        }
        
        strengths = calculate_or_breakout_strength(opening_range_results)
        
        assert strengths['BREAKOUT'] == 5.0  # 5% above ORH
        assert strengths['NO_BREAKOUT'] == 0.0
    
    def test_calculate_or_breakout_strength_empty(self):
        """Test breakout strength with empty results."""
        opening_range_results = {}
        
        strengths = calculate_or_breakout_strength(opening_range_results)
        
        assert strengths == {}


class TestSummary:
    """Test summary functions."""
    
    def test_summarize_opening_range_results(self):
        """Test opening range results summary."""
        opening_range_results = {
            'SYMBOL1': {
                'orh': 100,
                'orl': 99,
                'last_price': 101,
                'entry_triggered': True
            },
            'SYMBOL2': {
                'orh': 100,
                'orl': 99,
                'last_price': 99.5,
                'entry_triggered': False
            }
        }
        
        summary = summarize_opening_range_results(opening_range_results)
        
        assert summary['total_symbols'] == 2
        assert summary['triggered_count'] == 1
        assert summary['triggered_percentage'] == 50.0
        assert summary['avg_orh'] == 100.0
        assert summary['avg_orl'] == 99.0
        assert 'SYMBOL1' in summary['triggered_symbols']
    
    def test_summarize_opening_range_results_empty(self):
        """Test summary with empty results."""
        opening_range_results = {}
        
        summary = summarize_opening_range_results(opening_range_results)
        
        assert summary['total_symbols'] == 0
        assert summary['triggered_count'] == 0
        assert summary['triggered_percentage'] == 0
