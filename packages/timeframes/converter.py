"""
Timeframe conversion and utilities.

Centralizes timeframe parsing, conversion, and validation
to ensure consistency across the codebase.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta


# Timeframe to milliseconds mapping
TIMEFRAME_TO_MS: Dict[str, int] = {
    '1s': 1000,
    '5s': 5000,
    '15s': 15000,
    '30s': 30000,
    '1m': 60 * 1000,
    '3m': 3 * 60 * 1000,
    '5m': 5 * 60 * 1000,
    '15m': 15 * 60 * 1000,
    '30m': 30 * 60 * 1000,
    '1h': 60 * 60 * 1000,
    '2h': 2 * 60 * 60 * 1000,
    '4h': 4 * 60 * 60 * 1000,
    '6h': 6 * 60 * 60 * 1000,
    '8h': 8 * 60 * 60 * 1000,
    '12h': 12 * 60 * 60 * 1000,
    '1d': 24 * 60 * 60 * 1000,
    '3d': 3 * 24 * 60 * 60 * 1000,
    '1w': 7 * 24 * 60 * 60 * 1000,
    '1M': 30 * 24 * 60 * 60 * 1000,  # Approximate
}


# Timeframe to seconds mapping
TIMEFRAME_TO_SECONDS: Dict[str, int] = {
    '1s': 1,
    '5s': 5,
    '15s': 15,
    '30s': 30,
    '1m': 60,
    '3m': 3 * 60,
    '5m': 5 * 60,
    '15m': 15 * 60,
    '30m': 30 * 60,
    '1h': 60 * 60,
    '2h': 2 * 60 * 60,
    '4h': 4 * 60 * 60,
    '6h': 6 * 60 * 60,
    '8h': 8 * 60 * 60,
    '12h': 12 * 60 * 60,
    '1d': 24 * 60 * 60,
    '3d': 3 * 24 * 60 * 60,
    '1w': 7 * 24 * 60 * 60,
    '1M': 30 * 24 * 60 * 60,  # Approximate
}


def timeframe_to_milliseconds(timeframe: str) -> int:
    """
    Convert timeframe string to milliseconds.
    
    Args:
        timeframe: Timeframe string (e.g., '1m', '1h', '1d')
        
    Returns:
        Duration in milliseconds
        
    Raises:
        ValueError: If timeframe is invalid
        
    Example:
        >>> timeframe_to_milliseconds('1h')
        3600000
    """
    if timeframe not in TIMEFRAME_TO_MS:
        raise ValueError(f"Invalid timeframe: {timeframe}")
    
    return TIMEFRAME_TO_MS[timeframe]


def timeframe_to_seconds(timeframe: str) -> int:
    """
    Convert timeframe string to seconds.
    
    Args:
        timeframe: Timeframe string (e.g., '1m', '1h', '1d')
        
    Returns:
        Duration in seconds
        
    Example:
        >>> timeframe_to_seconds('1h')
        3600
    """
    if timeframe not in TIMEFRAME_TO_SECONDS:
        raise ValueError(f"Invalid timeframe: {timeframe}")
    
    return TIMEFRAME_TO_SECONDS[timeframe]


def timeframe_to_timedelta(timeframe: str) -> timedelta:
    """
    Convert timeframe string to timedelta object.
    
    Args:
        timeframe: Timeframe string
        
    Returns:
        timedelta object
    """
    seconds = timeframe_to_seconds(timeframe)
    return timedelta(seconds=seconds)


def validate_timeframe(timeframe: str) -> bool:
    """
    Check if timeframe is valid.
    
    Args:
        timeframe: Timeframe string to validate
        
    Returns:
        True if valid, False otherwise
    """
    return timeframe in TIMEFRAME_TO_MS


def get_supported_timeframes() -> List[str]:
    """
    Get list of supported timeframes.
    
    Returns:
        List of timeframe strings
    """
    return list(TIMEFRAME_TO_MS.keys())


def align_timestamp_to_timeframe(timestamp_ms: int, timeframe: str) -> int:
    """
    Align timestamp to timeframe boundary.
    
    For example, if timeframe is '1h', align to the start of the hour.
    
    Args:
        timestamp_ms: Timestamp in milliseconds
        timeframe: Timeframe string
        
    Returns:
        Aligned timestamp in milliseconds
        
    Example:
        >>> align_timestamp_to_timeframe(1609459265000, '1h')
        # Returns timestamp for start of hour
    """
    tf_ms = timeframe_to_milliseconds(timeframe)
    return (timestamp_ms // tf_ms) * tf_ms


def get_next_candle_open_time(timestamp_ms: int, timeframe: str) -> int:
    """
    Get the open time of the next candle.
    
    Args:
        timestamp_ms: Current timestamp in milliseconds
        timeframe: Timeframe string
        
    Returns:
        Next candle open time in milliseconds
    """
    tf_ms = timeframe_to_milliseconds(timeframe)
    aligned = align_timestamp_to_timeframe(timestamp_ms, timeframe)
    return aligned + tf_ms


def get_candle_open_time(timestamp_ms: int, timeframe: str) -> int:
    """
    Get the open time of the candle containing this timestamp.
    
    Args:
        timestamp_ms: Timestamp in milliseconds
        timeframe: Timeframe string
        
    Returns:
        Candle open time in milliseconds
    """
    return align_timestamp_to_timeframe(timestamp_ms, timeframe)


def is_candle_closed(timestamp_ms: int, timeframe: str, current_time_ms: int) -> bool:
    """
    Check if a candle is closed (complete).
    
    Args:
        timestamp_ms: Candle open timestamp
        timeframe: Timeframe string
        current_time_ms: Current timestamp
        
    Returns:
        True if candle is closed
    """
    next_open = get_next_candle_open_time(timestamp_ms, timeframe)
    return current_time_ms >= next_open


def get_candles_between(
    start_ms: int, end_ms: int, timeframe: str
) -> List[int]:
    """
    Get list of candle open timestamps between start and end.
    
    Args:
        start_ms: Start timestamp
        end_ms: End timestamp
        timeframe: Timeframe string
        
    Returns:
        List of candle open timestamps
        
    Example:
        >>> get_candles_between(
        ...     1609459200000,  # 2021-01-01 00:00:00
        ...     1609462800000,  # 2021-01-01 01:00:00
        ...     '1h'
        ... )
        [1609459200000]  # One 1h candle
    """
    tf_ms = timeframe_to_milliseconds(timeframe)
    
    # Align start to timeframe boundary
    current = align_timestamp_to_timeframe(start_ms, timeframe)
    
    candles = []
    while current < end_ms:
        candles.append(current)
        current += tf_ms
    
    return candles


def count_candles_between(start_ms: int, end_ms: int, timeframe: str) -> int:
    """
    Count number of candles between start and end timestamps.
    
    Args:
        start_ms: Start timestamp
        end_ms: End timestamp
        timeframe: Timeframe string
        
    Returns:
        Number of candles
    """
    tf_ms = timeframe_to_milliseconds(timeframe)
    return int((end_ms - start_ms) / tf_ms)


def format_timeframe_human(timeframe: str) -> str:
    """
    Convert timeframe to human-readable format.
    
    Args:
        timeframe: Timeframe string
        
    Returns:
        Human-readable string
        
    Example:
        >>> format_timeframe_human('1h')
        '1 hour'
        >>> format_timeframe_human('4h')
        '4 hours'
    """
    mapping = {
        's': 'second',
        'm': 'minute',
        'h': 'hour',
        'd': 'day',
        'w': 'week',
        'M': 'month',
    }
    
    # Parse timeframe
    unit = timeframe[-1]
    value = int(timeframe[:-1])
    
    if unit not in mapping:
        return timeframe
    
    unit_name = mapping[unit]
    if value > 1:
        unit_name += 's'
    
    return f"{value} {unit_name}"


def get_smaller_timeframe(timeframe: str) -> Optional[str]:
    """
    Get the next smaller standard timeframe.
    
    Args:
        timeframe: Current timeframe
        
    Returns:
        Smaller timeframe or None if already smallest
        
    Example:
        >>> get_smaller_timeframe('1h')
        '15m'
    """
    ordered = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
    
    if timeframe not in ordered:
        return None
    
    idx = ordered.index(timeframe)
    if idx == 0:
        return None
    
    return ordered[idx - 1]


def get_larger_timeframe(timeframe: str) -> Optional[str]:
    """
    Get the next larger standard timeframe.
    
    Args:
        timeframe: Current timeframe
        
    Returns:
        Larger timeframe or None if already largest
        
    Example:
        >>> get_larger_timeframe('1h')
        '2h'
    """
    ordered = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
    
    if timeframe not in ordered:
        return None
    
    idx = ordered.index(timeframe)
    if idx == len(ordered) - 1:
        return None
    
    return ordered[idx + 1]
