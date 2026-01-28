"""Unit tests for packages/strategies/condition_evaluator.py"""

import pytest
import pandas as pd
import numpy as np
from packages.strategies.condition_evaluator import ConditionEvaluator


class TestConditionEvaluator:
    """Test ConditionEvaluator for dynamic YAML strategy conditions."""
    
    @pytest.fixture
    def evaluator(self):
        """Create ConditionEvaluator instance."""
        # ConditionEvaluator needs indicators dict and context dict
        indicators = {
            'RSI': 50.0,
            'SMA': 102.0,
            'EMA': 101.0,
            'MACD_HIST': 0.5,
            'VWAP': 103.0
        }
        context = {
            'PRICE': 105.0,
            'VOLUME': 2000.0,
            'PNL_PCT': 2.5
        }
        return ConditionEvaluator(indicators, context)
    
    @pytest.fixture
    def sample_data(self):
        """Create sample market data."""
        return {
            'RSI': pd.Series([30, 40, 50, 60, 70]),
            'SMA': pd.Series([100, 101, 102, 103, 104]),
            'EMA': pd.Series([99, 100, 101, 102, 103]),
            'PRICE': pd.Series([105, 106, 107, 108, 109]),
            'VOLUME': pd.Series([1000, 1500, 2000, 2500, 3000]),
        }
    
    def test_simple_comparison_less_than(self, evaluator, sample_data):
        """Test simple less than comparison."""
        condition = "RSI < 50"
        result = evaluator.evaluate(condition, sample_data)
        
        # RSI values: [30, 40, 50, 60, 70]
        # RSI < 50: [True, True, False, False, False]
        assert result.iloc[0] == True
        assert result.iloc[1] == True
        assert result.iloc[2] == False
    
    def test_simple_comparison_greater_than(self, evaluator, sample_data):
        """Test simple greater than comparison."""
        condition = "RSI > 50"
        result = evaluator.evaluate(condition, sample_data)
        
        # RSI > 50: [False, False, False, True, True]
        assert result.iloc[3] == True
        assert result.iloc[4] == True
        assert result.iloc[0] == False
    
    def test_comparison_with_equals(self, evaluator, sample_data):
        """Test less than or equal comparison."""
        condition = "RSI <= 50"
        result = evaluator.evaluate(condition, sample_data)
        
        # RSI <= 50: [True, True, True, False, False]
        assert result.iloc[0] == True
        assert result.iloc[2] == True
        assert result.iloc[3] == False
    
    def test_indicator_crossover(self, evaluator, sample_data):
        """Test indicator crossover condition."""
        condition = "PRICE > SMA"
        result = evaluator.evaluate(condition, sample_data)
        
        # PRICE: [105, 106, 107, 108, 109]
        # SMA:   [100, 101, 102, 103, 104]
        # All True since PRICE > SMA for all values
        assert result.all()
    
    def test_and_condition(self, evaluator, sample_data):
        """Test AND logical operator."""
        condition = "RSI < 50 AND PRICE > SMA"
        result = evaluator.evaluate(condition, sample_data)
        
        # RSI < 50: [True, True, False, False, False]
        # PRICE > SMA: [True, True, True, True, True]
        # AND: [True, True, False, False, False]
        assert result.iloc[0] == True
        assert result.iloc[1] == True
        assert result.iloc[2] == False
    
    def test_or_condition(self, evaluator, sample_data):
        """Test OR logical operator."""
        condition = "RSI < 30 OR RSI > 70"
        result = evaluator.evaluate(condition, sample_data)
        
        # RSI: [30, 40, 50, 60, 70]
        # RSI < 30: [False, False, False, False, False]
        # RSI > 70: [False, False, False, False, False]
        # OR: [False, False, False, False, False]
        assert not result.any()
    
    def test_oversold_condition(self, evaluator):
        """Test typical oversold condition."""
        data = {'RSI': pd.Series([25, 20, 30, 35])}
        condition = "RSI < 30"
        result = evaluator.evaluate(condition, data)
        
        assert result.iloc[0] == True
        assert result.iloc[1] == True
        assert result.iloc[2] == False
    
    def test_overbought_condition(self, evaluator):
        """Test typical overbought condition."""
        data = {'RSI': pd.Series([65, 70, 75, 80])}
        condition = "RSI > 70"
        result = evaluator.evaluate(condition, data)
        
        assert result.iloc[0] == False
        assert result.iloc[1] == False
        assert result.iloc[2] == True
        assert result.iloc[3] == True
    
    def test_ma_crossover_bullish(self, evaluator):
        """Test bullish MA crossover."""
        data = {
            'SMA_fast': pd.Series([98, 99, 101, 103]),
            'SMA_slow': pd.Series([100, 100, 100, 100]),
        }
        condition = "SMA_fast > SMA_slow"
        result = evaluator.evaluate(condition, data)
        
        # Crossover happens at index 2
        assert result.iloc[0] == False
        assert result.iloc[1] == False
        assert result.iloc[2] == True
        assert result.iloc[3] == True
    
    def test_volume_spike(self, evaluator):
        """Test volume spike condition."""
        data = {
            'VOLUME': pd.Series([1000, 1100, 3000, 1200]),
            'VOLUME_MA': pd.Series([1000, 1050, 1367, 1575]),
        }
        condition = "VOLUME > VOLUME_MA * 2"
        # Note: This tests multiplication which we need to support
        # For now, we'll skip since our evaluator doesn't support arithmetic
        # TODO: Add arithmetic operator support if needed
        pytest.skip("Arithmetic operators not yet supported")
    
    def test_complex_entry_condition(self, evaluator):
        """Test complex multi-indicator entry."""
        data = {
            'RSI': pd.Series([25, 28, 35, 40]),
            'PRICE': pd.Series([98, 99, 101, 103]),
            'SMA': pd.Series([100, 100, 100, 100]),
            'VOLUME': pd.Series([5000, 6000, 7000, 5500]),
        }
        condition = "RSI < 30 AND PRICE < SMA AND VOLUME > 5000"
        result = evaluator.evaluate(condition, data)
        
        # RSI < 30: [True, True, False, False]
        # PRICE < SMA: [True, True, False, False]
        # VOLUME > 5000: [False, True, True, True]
        # AND: [False, True, False, False]
        assert result.iloc[0] == False  # Volume not > 5000
        assert result.iloc[1] == True   # All conditions met
        assert result.iloc[2] == False  # RSI and PRICE conditions failed
    
    def test_range_bound_condition(self, evaluator):
        """Test checking if value is in range."""
        data = {'RSI': pd.Series([25, 40, 50, 60, 75])}
        condition = "RSI > 30 AND RSI < 70"
        result = evaluator.evaluate(condition, data)
        
        # In range (30, 70): [False, True, True, True, False]
        assert result.iloc[0] == False
        assert result.iloc[1] == True
        assert result.iloc[2] == True
        assert result.iloc[3] == True
        assert result.iloc[4] == False
    
    def test_missing_indicator(self, evaluator, sample_data):
        """Test evaluation with missing indicator."""
        condition = "MISSING < 0"
        # Missing indicators should return False for all rows
        result = evaluator.evaluate(condition, sample_data)
        assert not result.any()
    
    def test_invalid_syntax(self, evaluator, sample_data):
        """Test evaluation with invalid syntax."""
        condition = "RSI <> 50"  # Invalid operator
        
        with pytest.raises((SyntaxError, ValueError)):
            evaluator.evaluate(condition, sample_data)
    
    def test_empty_condition(self, evaluator, sample_data):
        """Test evaluation with empty condition."""
        condition = ""
        
        with pytest.raises((ValueError, SyntaxError)):
            evaluator.evaluate(condition, sample_data)
    
    def test_percentage_change_condition(self, evaluator):
        """Test percentage change condition - skip as requires arithmetic."""
        # Arithmetic operators not supported yet
        pytest.skip("Arithmetic operators not yet supported")


class TestConditionEvaluatorEdgeCases:
    """Test edge cases for condition evaluation."""
    
    @pytest.fixture
    def evaluator(self):
        """Create ConditionEvaluator instance."""
        indicators = {'RSI': 50.0, 'SMA': 100.0}
        context = {'PRICE': 100.0}
        return ConditionEvaluator(indicators, context)
    
    def test_all_nan_series(self, evaluator):
        """Test evaluation with all NaN values."""
        data = {'RSI': pd.Series([np.nan, np.nan, np.nan])}
        condition = "RSI < 50"
        result = evaluator.evaluate(condition, data)
        
        # Should return False for NaN comparisons
        assert not result.any()
    
    def test_mixed_nan_series(self, evaluator):
        """Test evaluation with mixed NaN and valid values."""
        data = {'RSI': pd.Series([30, np.nan, 70, 40, np.nan])}
        condition = "RSI < 50"
        result = evaluator.evaluate(condition, data)
        
        # Only evaluate non-NaN values
        assert result.iloc[0] == True
        assert result.iloc[2] == False
        assert result.iloc[3] == True
    
    def test_single_value_series(self, evaluator):
        """Test evaluation with single value."""
        data = {'RSI': pd.Series([45])}
        condition = "RSI < 50"
        result = evaluator.evaluate(condition, data)
        
        assert len(result) == 1
        assert result.iloc[0] == True
    
    def test_boolean_result_type(self, evaluator):
        """Test that result is always boolean Series."""
        data = {'RSI': pd.Series([30, 50, 70])}
        condition = "RSI < 50"
        result = evaluator.evaluate(condition, data)
        
        assert isinstance(result, (pd.Series, pd.core.series.Series))
        assert result.dtype == bool


class TestStrategyConditionPatterns:
    """Test realistic strategy condition patterns."""
    
    @pytest.fixture
    def evaluator(self):
        """Create ConditionEvaluator instance."""
        indicators = {'RSI': 30.0, 'SMA_10': 100.0, 'SMA_20': 98.0}
        context = {'PRICE': 105.0, 'VOLUME': 2000.0}
        return ConditionEvaluator(indicators, context)
    
    def test_rsi_mean_reversion_entry(self, evaluator):
        """Test RSI mean reversion entry condition."""
        data = {'RSI': pd.Series([28, 25, 32, 40, 50])}
        condition = "RSI < 30"
        result = evaluator.evaluate(condition, data)
        
        # Entry signals when oversold
        assert result.iloc[0] == True
        assert result.iloc[1] == True
        assert result.iloc[2] == False
    
    def test_rsi_mean_reversion_exit(self, evaluator):
        """Test RSI mean reversion exit condition."""
        data = {'RSI': pd.Series([30, 50, 68, 72, 65])}
        condition = "RSI > 70"
        result = evaluator.evaluate(condition, data)
        
        # Exit signals when overbought
        assert result.iloc[3] == True
    
    def test_ma_crossover_entry(self, evaluator):
        """Test MA crossover entry condition."""
        data = {
            'SMA_50': pd.Series([100, 101, 103, 105, 107]),
            'SMA_200': pd.Series([102, 102, 102, 102, 102]),
        }
        condition = "SMA_50 > SMA_200"
        result = evaluator.evaluate(condition, data)
        
        # Golden cross at index 2
        assert result.iloc[0] == False
        assert result.iloc[1] == False
        assert result.iloc[2] == True
    
    def test_volume_confirmation(self, evaluator):
        """Test volume confirmation pattern."""
        data = {
            'RSI': pd.Series([25, 28, 35, 40]),
            'VOLUME': pd.Series([8000, 12000, 15000, 9000]),
            'VOLUME_MA': pd.Series([10000, 10000, 10000, 10000]),
        }
        condition = "RSI < 30 AND VOLUME > VOLUME_MA"
        result = evaluator.evaluate(condition, data)
        
        # Entry when oversold AND volume confirms
        assert result.iloc[1] == True  # RSI=28, VOLUME=12000>10000
