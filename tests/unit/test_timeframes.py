"""Unit tests for packages/timeframes/converter.py"""

import pytest
from datetime import datetime, timedelta
from packages.timeframes.converter import (
    TIMEFRAME_TO_MS,
    TIMEFRAME_TO_SECONDS,
    timeframe_to_milliseconds,
    timeframe_to_seconds,
    align_timestamp_to_timeframe,
    get_candles_between,
    count_candles_between,
    get_smaller_timeframe,
    get_larger_timeframe,
    format_timeframe_human,
    is_candle_closed,
    validate_timeframe,
)


class TestTimeframeConstants:
    """Test timeframe constant dictionaries."""
    
    def test_timeframe_ms_dict(self):
        """Test TIMEFRAME_TO_MS values."""
        assert TIMEFRAME_TO_MS['1m'] == 60 * 1000
        assert TIMEFRAME_TO_MS['5m'] == 5 * 60 * 1000
        assert TIMEFRAME_TO_MS['1h'] == 60 * 60 * 1000
        assert TIMEFRAME_TO_MS['1d'] == 24 * 60 * 60 * 1000
    
    def test_timeframe_seconds_dict(self):
        """Test TIMEFRAME_TO_SECONDS values."""
        assert TIMEFRAME_TO_SECONDS['1m'] == 60
        assert TIMEFRAME_TO_SECONDS['5m'] == 5 * 60
        assert TIMEFRAME_TO_SECONDS['1h'] == 60 * 60
        assert TIMEFRAME_TO_SECONDS['1d'] == 24 * 60 * 60


class TestTimeframeConversion:
    """Test timeframe conversion functions."""
    
    def test_timeframe_to_milliseconds(self):
        """Test conversion to milliseconds."""
        assert timeframe_to_milliseconds('1m') == 60000
        assert timeframe_to_milliseconds('5m') == 300000
        assert timeframe_to_milliseconds('1h') == 3600000
        assert timeframe_to_milliseconds('1d') == 86400000
    
    def test_timeframe_to_milliseconds_invalid(self):
        """Test invalid timeframe raises ValueError."""
        with pytest.raises(ValueError, match="Invalid timeframe"):
            timeframe_to_milliseconds('invalid')
    
    def test_timeframe_to_seconds(self):
        """Test conversion to seconds."""
        assert timeframe_to_seconds('1m') == 60
        assert timeframe_to_seconds('5m') == 300
        assert timeframe_to_seconds('1h') == 3600
        assert timeframe_to_seconds('1d') == 86400
    
    def test_timeframe_to_seconds_invalid(self):
        """Test invalid timeframe raises ValueError."""
        with pytest.raises(ValueError, match="Invalid timeframe"):
            timeframe_to_seconds('invalid')


class TestTimestampAlignment:
    """Test timestamp alignment to timeframe."""
    
    def test_align_1m_timeframe(self):
        """Test alignment to 1-minute boundary."""
        # 2024-01-01 10:35:45
        ts = int(datetime(2024, 1, 1, 10, 35, 45).timestamp() * 1000)
        aligned = align_timestamp_to_timeframe(ts, '1m')
        
        # Should align to 2024-01-01 10:35:00
        expected = int(datetime(2024, 1, 1, 10, 35, 0).timestamp() * 1000)
        assert aligned == expected
    
    def test_align_5m_timeframe(self):
        """Test alignment to 5-minute boundary."""
        # 2024-01-01 10:37:30
        ts = int(datetime(2024, 1, 1, 10, 37, 30).timestamp() * 1000)
        aligned = align_timestamp_to_timeframe(ts, '5m')
        
        # Should align to 2024-01-01 10:35:00
        expected = int(datetime(2024, 1, 1, 10, 35, 0).timestamp() * 1000)
        assert aligned == expected
    
    def test_align_1h_timeframe(self):
        """Test alignment to 1-hour boundary."""
        # 2024-01-01 10:45:30
        ts = int(datetime(2024, 1, 1, 10, 45, 30).timestamp() * 1000)
        aligned = align_timestamp_to_timeframe(ts, '1h')
        
        # Should align to 2024-01-01 10:00:00
        expected = int(datetime(2024, 1, 1, 10, 0, 0).timestamp() * 1000)
        assert aligned == expected
    
    def test_align_1d_timeframe(self):
        """Test alignment to 1-day boundary."""
        # 2024-01-01 15:30:00
        ts = int(datetime(2024, 1, 1, 15, 30, 0).timestamp() * 1000)
        aligned = align_timestamp_to_timeframe(ts, '1d')
        
        # Should align to 2024-01-01 00:00:00
        expected = int(datetime(2024, 1, 1, 0, 0, 0).timestamp() * 1000)
        assert aligned == expected


class TestCandleCounting:
    """Test candle counting between timestamps."""
    
    def test_count_candles_1m(self):
        """Test counting 1-minute candles."""
        start = int(datetime(2024, 1, 1, 10, 0, 0).timestamp() * 1000)
        end = int(datetime(2024, 1, 1, 10, 10, 0).timestamp() * 1000)
        
        count = count_candles_between(start, end, '1m')
        assert count == 10  # 10 minutes = 10 candles
    
    def test_count_candles_5m(self):
        """Test counting 5-minute candles."""
        start = int(datetime(2024, 1, 1, 10, 0, 0).timestamp() * 1000)
        end = int(datetime(2024, 1, 1, 11, 0, 0).timestamp() * 1000)
        
        count = count_candles_between(start, end, '5m')
        assert count == 12  # 60 minutes = 12 5-minute candles
    
    def test_count_candles_1h(self):
        """Test counting 1-hour candles."""
        start = int(datetime(2024, 1, 1, 10, 0, 0).timestamp() * 1000)
        end = int(datetime(2024, 1, 1, 20, 0, 0).timestamp() * 1000)
        
        count = count_candles_between(start, end, '1h')
        assert count == 10  # 10 hours = 10 candles
    
    def test_count_candles_1d(self):
        """Test counting 1-day candles."""
        start = int(datetime(2024, 1, 1, 0, 0, 0).timestamp() * 1000)
        end = int(datetime(2024, 1, 11, 0, 0, 0).timestamp() * 1000)
        
        count = count_candles_between(start, end, '1d')
        assert count == 10  # 10 days = 10 candles


class TestGetCandlesBetween:
    """Test generating list of candle timestamps."""
    
    def test_get_candles_1m(self):
        """Test generating 1-minute candles."""
        start = int(datetime(2024, 1, 1, 10, 0, 0).timestamp() * 1000)
        end = int(datetime(2024, 1, 1, 10, 5, 0).timestamp() * 1000)
        
        candles = get_candles_between(start, end, '1m')
        
        assert len(candles) == 5
        assert candles[0] == start
        assert candles[-1] == end - (60 * 1000)  # Last candle before end
    
    def test_get_candles_5m(self):
        """Test generating 5-minute candles."""
        start = int(datetime(2024, 1, 1, 10, 0, 0).timestamp() * 1000)
        end = int(datetime(2024, 1, 1, 10, 20, 0).timestamp() * 1000)
        
        candles = get_candles_between(start, end, '5m')
        
        assert len(candles) == 4
        # Verify spacing
        for i in range(1, len(candles)):
            assert candles[i] - candles[i-1] == 5 * 60 * 1000


class TestTimeframeNavigation:
    """Test getting smaller/larger timeframes."""
    
    def test_get_smaller_timeframe(self):
        """Test getting smaller timeframe."""
        assert get_smaller_timeframe('5m') == '3m'
        assert get_smaller_timeframe('15m') == '5m'
        assert get_smaller_timeframe('1h') == '30m'
        assert get_smaller_timeframe('1d') == '12h'
    
    def test_get_smaller_timeframe_minimum(self):
        """Test getting smaller than minimum timeframe."""
        assert get_smaller_timeframe('1m') is None  # No smaller timeframe
    
    def test_get_larger_timeframe(self):
        """Test getting larger timeframe."""
        assert get_larger_timeframe('1m') == '3m'
        assert get_larger_timeframe('3m') == '5m'
        assert get_larger_timeframe('5m') == '15m'
        assert get_larger_timeframe('1h') == '2h'
    
    def test_get_larger_timeframe_maximum(self):
        """Test getting larger than maximum timeframe."""
        assert get_larger_timeframe('1M') is None  # No larger timeframe


class TestFormatTimeframe:
    """Test human-readable timeframe formatting."""
    
    def test_format_minutes(self):
        """Test formatting minute timeframes."""
        assert format_timeframe_human('1m') == '1 minute'
        assert format_timeframe_human('5m') == '5 minutes'
        assert format_timeframe_human('15m') == '15 minutes'
    
    def test_format_hours(self):
        """Test formatting hour timeframes."""
        assert format_timeframe_human('1h') == '1 hour'
        assert format_timeframe_human('4h') == '4 hours'
    
    def test_format_days(self):
        """Test formatting day timeframes."""
        assert format_timeframe_human('1d') == '1 day'
    
    def test_format_weeks(self):
        """Test formatting week timeframes."""
        assert format_timeframe_human('1w') == '1 week'
    
    def test_format_months(self):
        """Test formatting month timeframes."""
        assert format_timeframe_human('1M') == '1 month'
    
    def test_format_invalid(self):
        """Test formatting invalid timeframe raises error."""
        with pytest.raises(ValueError):
            format_timeframe_human('invalid')


class TestCandleClosed:
    """Test checking if candle is closed."""
    
    def test_candle_closed_1m(self):
        """Test if 1-minute candle is closed."""
        # Candle at 10:00:00
        candle_ts = int(datetime(2024, 1, 1, 10, 0, 0).timestamp() * 1000)
        
        # Current time at 10:01:30 (candle is closed)
        current_ts = int(datetime(2024, 1, 1, 10, 1, 30).timestamp() * 1000)
        assert is_candle_closed(candle_ts, '1m', current_ts) is True
        
        # Current time at 10:00:30 (candle is forming)
        current_ts = int(datetime(2024, 1, 1, 10, 0, 30).timestamp() * 1000)
        assert is_candle_closed(candle_ts, '1m', current_ts) is False
    
    def test_candle_closed_1h(self):
        """Test if 1-hour candle is closed."""
        # Candle at 10:00:00
        candle_ts = int(datetime(2024, 1, 1, 10, 0, 0).timestamp() * 1000)
        
        # Current time at 11:30:00 (candle is closed)
        current_ts = int(datetime(2024, 1, 1, 11, 30, 0).timestamp() * 1000)
        assert is_candle_closed(candle_ts, '1h', current_ts) is True
        
        # Current time at 10:30:00 (candle is forming)
        current_ts = int(datetime(2024, 1, 1, 10, 30, 0).timestamp() * 1000)
        assert is_candle_closed(candle_ts, '1h', current_ts) is False


class TestValidateTimeframe:
    """Test timeframe validation."""
    
    def test_valid_timeframes(self):
        """Test valid timeframes."""
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '8h', '1d', '1w', '1M']
        for tf in valid_timeframes:
            assert validate_timeframe(tf) is True
    
    def test_invalid_timeframes(self):
        """Test invalid timeframes."""
        invalid_timeframes = ['', '1minute', '10m', '7d', 'invalid']
        for tf in invalid_timeframes:
            assert validate_timeframe(tf) is False
