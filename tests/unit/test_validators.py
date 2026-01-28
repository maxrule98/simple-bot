"""Unit tests for packages/utils/validators.py"""

import pytest
from datetime import datetime
from packages.utils.validators import (
    validate_symbol,
    validate_exchange,
    validate_price,
    validate_quantity,
    validate_timestamp,
    validate_percentage,
    validate_strategy_id,
    sanitize_symbol,
    sanitize_exchange,
    validate_candle_data,
    is_valid_indicator_name,
    normalize_timestamp,
)


class TestSymbolValidation:
    """Test symbol validation and sanitization."""
    
    def test_valid_symbols(self):
        """Test valid symbol formats."""
        assert validate_symbol("BTC/USDT") is True
        assert validate_symbol("ETH/USDT") is True
        assert validate_symbol("SOL/USDT") is True
        assert validate_symbol("BTC/USD") is True
    
    def test_invalid_symbols(self):
        """Test invalid symbol formats."""
        with pytest.raises(ValueError):
            validate_symbol("BTCUSDT")  # Missing slash
        with pytest.raises(ValueError):
            validate_symbol("BTC-USDT")  # Wrong separator
        with pytest.raises(ValueError):
            validate_symbol("BTC")  # No quote
        with pytest.raises(ValueError):
            validate_symbol("")  # Empty
        with pytest.raises(ValueError):
            validate_symbol("BTC/")  # Missing quote
        with pytest.raises(ValueError):
            validate_symbol("/USDT")  # Missing base
    
    def test_sanitize_symbol(self):
        """Test symbol sanitization."""
        assert sanitize_symbol("btc/usdt") == "BTC/USDT"
        assert sanitize_symbol("  BTC/USDT  ") == "BTC/USDT"
        assert sanitize_symbol("eth/usdt") == "ETH/USDT"


class TestExchangeValidation:
    """Test exchange validation and sanitization."""
    
    def test_valid_exchanges(self):
        """Test valid exchange names."""
        assert validate_exchange("mexc") is True
        assert validate_exchange("binance") is True
        assert validate_exchange("coinbase") is True
        assert validate_exchange("kraken") is True
    
    def test_invalid_exchanges(self):
        """Test invalid exchange names."""
        with pytest.raises(ValueError):
            validate_exchange("")
        with pytest.raises(ValueError):
            validate_exchange("INVALID")  # Must be lowercase
        with pytest.raises(ValueError):
            validate_exchange("exchange-name")  # No hyphens allowed
    
    def test_sanitize_exchange(self):
        """Test exchange sanitization."""
        assert sanitize_exchange("MEXC") == "mexc"
        assert sanitize_exchange("  Binance  ") == "binance"
        assert sanitize_exchange("COINBASE") == "coinbase"


class TestPriceValidation:
    """Test price validation."""
    
    def test_valid_prices(self):
        """Test valid price values."""
        assert validate_price(100.0) is True
        assert validate_price(0.001) is True
        assert validate_price(89000.50) is True
    
    def test_invalid_prices(self):
        """Test invalid price values."""
        with pytest.raises(ValueError):
            validate_price(0.0)  # Zero
        with pytest.raises(ValueError):
            validate_price(-100.0)  # Negative
        with pytest.raises(ValueError):
            validate_price(1e15)  # Unreasonably high


class TestQuantityValidation:
    """Test quantity validation."""
    
    def test_valid_quantities(self):
        """Test valid quantity values."""
        assert validate_quantity(0.001) is True
        assert validate_quantity(1.0) is True
        assert validate_quantity(100.5) is True
    
    def test_invalid_quantities(self):
        """Test invalid quantity values."""
        with pytest.raises(ValueError):
            validate_quantity(0.0)  # Zero
        with pytest.raises(ValueError):
            validate_quantity(-0.001)  # Negative


class TestTimestampValidation:
    """Test timestamp validation."""
    
    def test_valid_timestamps(self):
        """Test valid timestamp values."""
        now_ms = int(datetime.now().timestamp() * 1000)
        assert validate_timestamp(now_ms) is True
        assert validate_timestamp(1704067200000) is True  # 2024-01-01
    
    def test_invalid_timestamps(self):
        """Test invalid timestamp values."""
        with pytest.raises(ValueError):
            validate_timestamp(0)  # Too old
        with pytest.raises(ValueError):
            validate_timestamp(-1000)  # Negative
        with pytest.raises(ValueError):
            validate_timestamp(999999)  # Too small (not milliseconds)
    
    def test_future_timestamps(self):
        """Test future timestamps are accepted (within 2100)."""
        future_ms = int((datetime.now().timestamp() + 365*24*3600) * 1000)  # 1 year ahead
        # Should be valid as long as < year 2100
        assert validate_timestamp(future_ms) is True
        
        # But year 2200 should fail
        far_future_ms = int(datetime(2200, 1, 1).timestamp() * 1000)
        with pytest.raises(ValueError):
            validate_timestamp(far_future_ms)


class TestPercentageValidation:
    """Test percentage validation."""
    
    def test_valid_percentages(self):
        """Test valid percentage values."""
        assert validate_percentage(0.0) is True
        assert validate_percentage(50.0) is True
        assert validate_percentage(100.0) is True
        assert validate_percentage(2.5) is True
    
    def test_invalid_percentages(self):
        """Test invalid percentage values."""
        with pytest.raises(ValueError):
            validate_percentage(-1.0)  # Negative
        with pytest.raises(ValueError):
            validate_percentage(101.0)  # > 100


class TestStrategyIdValidation:
    """Test strategy ID validation."""
    
    def test_valid_strategy_ids(self):
        """Test valid strategy ID formats."""
        assert validate_strategy_id("btc-rsi-001") is True
        assert validate_strategy_id("eth-ma-crossover-001") is True
        assert validate_strategy_id("test-strategy-123") is True
    
    def test_invalid_strategy_ids(self):
        """Test invalid strategy ID formats."""
        with pytest.raises(ValueError):
            validate_strategy_id("")  # Empty
        with pytest.raises(ValueError):
            validate_strategy_id("a" * 101)  # Too long (>100 chars)
        with pytest.raises(ValueError):
            validate_strategy_id("invalid id with spaces")  # Spaces not allowed


class TestCandleDataValidation:
    """Test candle data validation."""
    
    def test_valid_candle(self, sample_candle_data):
        """Test valid candle data."""
        assert validate_candle_data(sample_candle_data) is True
    
    def test_invalid_high_low(self):
        """Test candle with high < low."""
        candle = {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'open': 100.0,
            'high': 95.0,  # Invalid
            'low': 105.0,
            'close': 100.0,
            'volume': 1000.0
        }
        with pytest.raises(ValueError):
            validate_candle_data(candle)
    
    def test_invalid_high(self):
        """Test candle with high < close."""
        candle = {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'open': 100.0,
            'high': 99.0,  # Invalid (< open)
            'low': 95.0,
            'close': 100.0,
            'volume': 1000.0
        }
        with pytest.raises(ValueError):
            validate_candle_data(candle)
    
    def test_invalid_low(self):
        """Test candle with low > close."""
        candle = {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'open': 100.0,
            'high': 105.0,
            'low': 101.0,  # Invalid (> close)
            'close': 100.0,
            'volume': 1000.0
        }
        with pytest.raises(ValueError):
            validate_candle_data(candle)
    
    def test_negative_volume(self):
        """Test candle with negative volume."""
        candle = {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'open': 100.0,
            'high': 105.0,
            'low': 95.0,
            'close': 100.0,
            'volume': -1000.0  # Invalid
        }
        with pytest.raises(ValueError):
            validate_candle_data(candle)
    
    def test_missing_fields(self):
        """Test candle with missing fields."""
        candle = {
            'timestamp': int(datetime.now().timestamp() * 1000),
            'open': 100.0,
            # Missing high, low, close, volume
        }
        with pytest.raises(ValueError):
            validate_candle_data(candle)


class TestIndicatorNameValidation:
    """Test indicator name validation."""
    
    def test_valid_indicator_names(self):
        """Test valid indicator names."""
        assert is_valid_indicator_name("RSI") is True
        assert is_valid_indicator_name("SMA") is True
        assert is_valid_indicator_name("EMA") is True
        assert is_valid_indicator_name("MACD") is True
    
    def test_invalid_indicator_names(self):
        """Test invalid indicator names."""
        assert is_valid_indicator_name("") is False
        assert is_valid_indicator_name("123") is False
        assert is_valid_indicator_name("invalid-indicator") is False


class TestTimestampNormalization:
    """Test timestamp normalization."""
    
    def test_normalize_milliseconds(self):
        """Test normalization of already-millisecond timestamps."""
        ts_ms = 1704067200000  # 2024-01-01 in milliseconds
        assert normalize_timestamp(ts_ms) == ts_ms
    
    def test_normalize_seconds(self):
        """Test normalization of second timestamps to milliseconds."""
        ts_s = 1704067200  # 2024-01-01 in seconds
        expected = ts_s * 1000
        assert normalize_timestamp(ts_s) == expected
    
    def test_current_timestamp(self):
        """Test normalization of current timestamp."""
        now_s = int(datetime.now().timestamp())
        now_ms = int(datetime.now().timestamp() * 1000)
        
        # Should convert seconds to milliseconds
        assert normalize_timestamp(now_s) == now_s * 1000
        
        # Should leave milliseconds unchanged
        assert normalize_timestamp(now_ms) == now_ms
