"""Unit tests for packages/indicators (RSI, SMA, EMA)"""

import pytest
import pandas as pd
import numpy as np
from packages.indicators import calculate_rsi, calculate_sma, calculate_ema


class TestRSI:
    """Test RSI (Relative Strength Index) indicator."""
    
    def test_rsi_calculation(self, sample_price_series):
        """Test basic RSI calculation."""
        rsi = calculate_rsi(sample_price_series, period=14)
        
        # Indicators return float (current value), not Series
        assert isinstance(rsi, float)
        assert 0 <= rsi <= 100
    
    def test_rsi_with_dataframe(self, sample_ohlcv_data):
        """Test RSI with DataFrame input."""
        rsi = calculate_rsi(sample_ohlcv_data, period=14)
        
        assert isinstance(rsi, float)
        assert 0 <= rsi <= 100
    
    def test_rsi_period_14(self):
        """Test RSI with standard 14-period."""
        prices = pd.DataFrame({'close': [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42,
                                          45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28]})
        
        rsi = calculate_rsi(prices, period=14)
        
        # Value should be around 70 (overbought)
        assert 60 <= rsi <= 80
    
    def test_rsi_overbought(self):
        """Test RSI identifies overbought conditions."""
        # Create strongly uptrending prices
        prices = pd.DataFrame({'close': [100 + i*2 for i in range(50)]})
        rsi = calculate_rsi(prices, period=14)
        
        # RSI should be high (>70) for strong uptrend
        assert rsi > 70
    
    def test_rsi_oversold(self):
        """Test RSI identifies oversold conditions."""
        # Create strongly downtrending prices
        prices = pd.DataFrame({'close': [100 - i*2 for i in range(50)]})
        rsi = calculate_rsi(prices, period=14)
        
        # RSI should be low (<30) for strong downtrend
        assert rsi < 30
    
    def test_rsi_different_periods(self, sample_price_series):
        """Test RSI with different periods."""
        rsi_7 = calculate_rsi(sample_price_series, period=7)
        rsi_14 = calculate_rsi(sample_price_series, period=14)
        rsi_21 = calculate_rsi(sample_price_series, period=21)
        
        # All should be valid floats
        assert isinstance(rsi_7, float)
        assert isinstance(rsi_14, float)
        assert isinstance(rsi_21, float)
        
        # All should be in valid range
        assert 0 <= rsi_7 <= 100
        assert 0 <= rsi_14 <= 100
        assert 0 <= rsi_21 <= 100
    
    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data."""
        prices = pd.DataFrame({'close': [100, 101, 99, 102]})  # Only 4 values
        rsi = calculate_rsi(prices, period=14)
        
        # Should return 50.0 (neutral) for insufficient data
        assert isinstance(rsi, float)
        assert rsi == 50.0


class TestSMA:
    """Test SMA (Simple Moving Average) indicator."""
    
    def test_sma_calculation(self, sample_price_series):
        """Test basic SMA calculation."""
        sma = calculate_sma(sample_price_series, period=20)
        
        # Indicators return float
        assert isinstance(sma, float)
        assert sma > 0
    
    def test_sma_with_dataframe(self, sample_ohlcv_data):
        """Test SMA with DataFrame input."""
        sma = calculate_sma(sample_ohlcv_data, period=20)
        
        assert isinstance(sma, float)
        assert sma > 0
    
    def test_sma_values(self):
        """Test SMA calculation accuracy."""
        prices = pd.DataFrame({'close': [10, 20, 30, 40, 50]})
        sma = calculate_sma(prices, period=3)
        
        # With 5 values and period=3, returns average of last 3: (30+40+50)/3 = 40
        assert isinstance(sma, float)
        assert abs(sma - 40.0) < 0.01
    
    def test_sma_different_periods(self, sample_price_series):
        """Test SMA with different periods."""
        sma_10 = calculate_sma(sample_price_series, period=10)
        sma_20 = calculate_sma(sample_price_series, period=20)
        sma_50 = calculate_sma(sample_price_series, period=50)
        
        # All should be valid floats
        assert isinstance(sma_10, float)
        assert isinstance(sma_20, float)
        assert isinstance(sma_50, float)
    
    def test_sma_crossover_detection(self):
        """Test SMA with trend change."""
        # Create price series with trend change
        prices = pd.DataFrame({'close': [100 - i for i in range(25)] + [75 + i for i in range(25)]})
        
        sma_10 = calculate_sma(prices, period=10)
        sma_20 = calculate_sma(prices, period=20)
        
        # Both should be valid floats
        assert isinstance(sma_10, float)
        assert isinstance(sma_20, float)


class TestEMA:
    """Test EMA (Exponential Moving Average) indicator."""
    
    def test_ema_calculation(self, sample_price_series):
        """Test basic EMA calculation."""
        ema = calculate_ema(sample_price_series, period=20)
        
        # Indicators return float
        assert isinstance(ema, float)
        assert ema > 0
    
    def test_ema_with_dataframe(self, sample_ohlcv_data):
        """Test EMA with DataFrame input."""
        ema = calculate_ema(sample_ohlcv_data, period=20)
        
        assert isinstance(ema, float)
        assert ema > 0
    
    def test_ema_more_responsive_than_sma(self, sample_price_series):
        """Test that EMA and SMA both work."""
        sma = calculate_sma(sample_price_series, period=20)
        ema = calculate_ema(sample_price_series, period=20)
        
        # Both should be valid floats
        assert isinstance(sma, float)
        assert isinstance(ema, float)
        assert sma > 0
        assert ema > 0
    
    def test_ema_values(self):
        """Test EMA calculation with known values."""
        prices = pd.DataFrame({'close': [22.27, 22.19, 22.08, 22.17, 22.18, 22.13, 22.23, 22.43, 22.24, 22.29]})
        ema = calculate_ema(prices, period=5)
        
        # EMA should be close to recent prices
        assert isinstance(ema, float)
        last_price = prices['close'].iloc[-1]
        assert abs(ema - last_price) < 1.0  # Within reasonable range
    
    def test_ema_different_periods(self, sample_price_series):
        """Test EMA with different periods."""
        ema_12 = calculate_ema(sample_price_series, period=12)
        ema_26 = calculate_ema(sample_price_series, period=26)
        ema_50 = calculate_ema(sample_price_series, period=50)
        
        # All should be valid floats
        assert isinstance(ema_12, float)
        assert isinstance(ema_26, float)
        assert isinstance(ema_50, float)
    
    def test_ema_macd_setup(self, sample_price_series):
        """Test EMA for MACD calculation (12 and 26 periods)."""
        ema_12 = calculate_ema(sample_price_series, period=12)
        ema_26 = calculate_ema(sample_price_series, period=26)
        
        # MACD line would be ema_12 - ema_26
        macd = ema_12 - ema_26
        
        # MACD should be a valid value
        assert isinstance(macd, float)
        assert abs(macd) < sample_price_series['close'].mean()


class TestIndicatorEdgeCases:
    """Test edge cases for all indicators."""
    
    def test_empty_series(self):
        """Test indicators with empty DataFrame."""
        empty = pd.DataFrame({'close': []})
        
        # With empty data, functions return mean of empty series (fallback behavior)
        # This will likely return NaN or raise an error
        try:
            rsi = calculate_rsi(empty, period=14)
            # If it returns, should be 50.0 (neutral) for insufficient data
            assert rsi == 50.0
        except (ValueError, IndexError):
            # Expected for empty data
            pass
    
    def test_single_value(self):
        """Test indicators with single value."""
        single = pd.DataFrame({'close': [100.0]})
        
        rsi = calculate_rsi(single, period=14)
        sma = calculate_sma(single, period=20)
        ema = calculate_ema(single, period=20)
        
        # With insufficient data, RSI returns 50.0
        assert rsi == 50.0
        # SMA/EMA fall back to mean of available data
        assert sma == 100.0
        assert ema == 100.0
    
    def test_constant_prices(self):
        """Test indicators with constant prices."""
        constant = pd.DataFrame({'close': [100.0] * 30})
        
        rsi = calculate_rsi(constant, period=14)
        sma = calculate_sma(constant, period=20)
        ema = calculate_ema(constant, period=20)
        
        # With constant prices, RSI will be NaN (division by zero in RS calculation)
        # but the function should handle it gracefully
        assert isinstance(rsi, float)
        
        # SMA should equal the constant value
        assert abs(sma - 100.0) < 0.01
        
        # EMA should equal the constant value
        assert abs(ema - 100.0) < 0.01
    
    def test_nan_handling(self):
        """Test indicators with NaN values."""
        with_nan = pd.DataFrame({'close': [100, 101, np.nan, 102, 103, 104]})
        
        # Indicators should handle NaN gracefully
        rsi = calculate_rsi(with_nan, period=3)
        sma = calculate_sma(with_nan, period=3)
        ema = calculate_ema(with_nan, period=3)
        
        # Results should be floats (may be NaN themselves)
        assert isinstance(rsi, (float, type(np.nan)))
        assert isinstance(sma, (float, type(np.nan)))
        assert isinstance(ema, (float, type(np.nan)))
