"""
Validation utilities for input validation and data sanitization.
"""

import re
from typing import Any, Optional


def validate_symbol(symbol: str) -> bool:
    """
    Validate trading symbol format.
    
    Args:
        symbol: Trading pair (e.g., 'BTC/USDT')
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If symbol is invalid
    """
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string")
    
    # Standard format: BASE/QUOTE
    if '/' not in symbol:
        raise ValueError(f"Invalid symbol format: {symbol}. Expected format: BASE/QUOTE")
    
    parts = symbol.split('/')
    if len(parts) != 2:
        raise ValueError(f"Invalid symbol format: {symbol}")
    
    base, quote = parts
    if not base or not quote:
        raise ValueError(f"Invalid symbol: empty base or quote")
    
    # Check for valid characters (alphanumeric only)
    if not re.match(r'^[A-Z0-9]+$', base) or not re.match(r'^[A-Z0-9]+$', quote):
        raise ValueError(f"Symbol must contain only uppercase letters and numbers")
    
    return True


def validate_exchange(exchange: str) -> bool:
    """
    Validate exchange name.
    
    Args:
        exchange: Exchange name (e.g., 'mexc', 'binance')
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If exchange is invalid
    """
    if not exchange or not isinstance(exchange, str):
        raise ValueError("Exchange must be a non-empty string")
    
    # Lowercase alphanumeric only
    if not re.match(r'^[a-z0-9]+$', exchange):
        raise ValueError(
            f"Invalid exchange name: {exchange}. Must be lowercase alphanumeric"
        )
    
    return True


def validate_price(price: float) -> bool:
    """
    Validate price value.
    
    Args:
        price: Price to validate
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If price is invalid
    """
    if not isinstance(price, (int, float)):
        raise ValueError("Price must be a number")
    
    if price <= 0:
        raise ValueError("Price must be positive")
    
    if price > 1e10:  # Sanity check
        raise ValueError("Price unreasonably high")
    
    return True


def validate_quantity(quantity: float) -> bool:
    """
    Validate quantity value.
    
    Args:
        quantity: Quantity to validate
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If quantity is invalid
    """
    if not isinstance(quantity, (int, float)):
        raise ValueError("Quantity must be a number")
    
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    
    return True


def validate_timestamp(timestamp: int) -> bool:
    """
    Validate timestamp value.
    
    Args:
        timestamp: Unix timestamp in milliseconds
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If timestamp is invalid
    """
    if not isinstance(timestamp, int):
        raise ValueError("Timestamp must be an integer")
    
    # Check reasonable range (between 2000 and 2100)
    min_ts = 946684800000  # 2000-01-01
    max_ts = 4102444800000  # 2100-01-01
    
    if timestamp < min_ts or timestamp > max_ts:
        raise ValueError(f"Timestamp out of reasonable range: {timestamp}")
    
    return True


def validate_percentage(value: float, min_val: float = 0.0, max_val: float = 100.0) -> bool:
    """
    Validate percentage value.
    
    Args:
        value: Percentage value
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If percentage is invalid
    """
    if not isinstance(value, (int, float)):
        raise ValueError("Percentage must be a number")
    
    if value < min_val or value > max_val:
        raise ValueError(
            f"Percentage must be between {min_val} and {max_val}, got {value}"
        )
    
    return True


def validate_strategy_id(strategy_id: str) -> bool:
    """
    Validate strategy ID format.
    
    Args:
        strategy_id: Strategy identifier
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If strategy ID is invalid
    """
    if not strategy_id or not isinstance(strategy_id, str):
        raise ValueError("Strategy ID must be a non-empty string")
    
    # Alphanumeric, hyphens, underscores only
    if not re.match(r'^[a-zA-Z0-9_-]+$', strategy_id):
        raise ValueError(
            f"Invalid strategy ID: {strategy_id}. "
            f"Must contain only letters, numbers, hyphens, and underscores"
        )
    
    if len(strategy_id) > 100:
        raise ValueError("Strategy ID too long (max 100 characters)")
    
    return True


def sanitize_symbol(symbol: str) -> str:
    """
    Sanitize and normalize symbol format.
    
    Args:
        symbol: Trading pair
        
    Returns:
        Normalized symbol (uppercase, standard format)
        
    Example:
        >>> sanitize_symbol('btc/usdt')
        'BTC/USDT'
        >>> sanitize_symbol('btcusdt')
        'BTC/USDT' # If recognizable
    """
    # Remove whitespace
    symbol = symbol.strip().upper()
    
    # If already has slash, validate and return
    if '/' in symbol:
        validate_symbol(symbol)
        return symbol
    
    # Try to split common pairs (basic heuristic)
    # This is limited - may not work for all pairs
    common_quotes = ['USDT', 'USDC', 'USD', 'BTC', 'ETH', 'EUR', 'GBP']
    
    for quote in common_quotes:
        if symbol.endswith(quote):
            base = symbol[:-len(quote)]
            if base:
                result = f"{base}/{quote}"
                try:
                    validate_symbol(result)
                    return result
                except ValueError:
                    continue
    
    # Can't parse, return as-is and let validation fail later
    return symbol


def sanitize_exchange(exchange: str) -> str:
    """
    Sanitize exchange name.
    
    Args:
        exchange: Exchange name
        
    Returns:
        Normalized exchange name (lowercase)
    """
    return exchange.strip().lower()


def validate_candle_data(candle: dict) -> bool:
    """
    Validate OHLCV candle data structure.
    
    Args:
        candle: Candle dictionary
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If candle data is invalid
    """
    required_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    
    for field in required_fields:
        if field not in candle:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate timestamp
    validate_timestamp(candle['timestamp'])
    
    # Validate OHLC prices
    for field in ['open', 'high', 'low', 'close']:
        validate_price(candle[field])
    
    # Validate volume
    if candle['volume'] < 0:
        raise ValueError("Volume cannot be negative")
    
    # Validate price relationships
    if candle['high'] < candle['low']:
        raise ValueError("High price cannot be less than low price")
    
    if candle['high'] < candle['open'] or candle['high'] < candle['close']:
        raise ValueError("High price must be >= open and close")
    
    if candle['low'] > candle['open'] or candle['low'] > candle['close']:
        raise ValueError("Low price must be <= open and close")
    
    return True


def is_valid_indicator_name(name: str) -> bool:
    """
    Check if indicator name is valid.
    
    Args:
        name: Indicator name
        
    Returns:
        True if valid format
    """
    if not name or not isinstance(name, str):
        return False
    
    # Uppercase letters, numbers, underscores
    return bool(re.match(r'^[A-Z_][A-Z0-9_]*$', name))
