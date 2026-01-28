"""
Risk management calculations and position sizing.

Centralizes all risk-related calculations to ensure consistency
and avoid duplication across strategies.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class RiskParameters:
    """Risk management parameters for a strategy."""
    
    position_size_pct: float  # % of capital to risk per trade (e.g., 2.0 = 2%)
    stop_loss_pct: float  # % stop loss (e.g., 1.0 = 1%)
    take_profit_pct: float  # % take profit (e.g., 3.0 = 3%)
    max_position_size: Optional[float] = None  # Max position size in base currency
    max_daily_trades: Optional[int] = None  # Max trades per day
    max_daily_loss_pct: Optional[float] = None  # Max daily loss % before stopping
    trailing_stop_pct: Optional[float] = None  # Trailing stop %
    risk_reward_ratio: float = 2.0  # Minimum risk/reward ratio


def calculate_position_size(
    capital: float,
    risk_pct: float,
    entry_price: float,
    stop_loss_price: float,
    max_size: Optional[float] = None,
) -> float:
    """
    Calculate position size based on fixed percentage risk.
    
    Formula: Position Size = (Capital * Risk%) / (Entry Price - Stop Loss Price)
    
    Args:
        capital: Total available capital
        risk_pct: % of capital to risk (e.g., 2.0 = 2%)
        entry_price: Entry price
        stop_loss_price: Stop loss price
        max_size: Optional maximum position size (in base currency)
        
    Returns:
        Position size in base currency
        
    Example:
        >>> calculate_position_size(10000, 2.0, 100, 98)
        # Risk $200 (2% of $10k) with $2 stop = 100 units
        100.0
    """
    if entry_price <= 0 or stop_loss_price <= 0:
        raise ValueError("Prices must be positive")
    
    if stop_loss_price >= entry_price:
        raise ValueError("Stop loss must be below entry price for longs")
    
    # Amount to risk in dollars
    risk_amount = capital * (risk_pct / 100)
    
    # Risk per unit
    risk_per_unit = abs(entry_price - stop_loss_price)
    
    # Position size
    position_size = risk_amount / risk_per_unit
    
    # Apply max size limit if specified
    if max_size is not None:
        position_size = min(position_size, max_size)
    
    return position_size


def calculate_stop_loss_price(
    entry_price: float,
    stop_loss_pct: float,
    side: str = 'long',
) -> float:
    """
    Calculate stop loss price from percentage.
    
    Args:
        entry_price: Entry price
        stop_loss_pct: Stop loss percentage (e.g., 2.0 = 2%)
        side: 'long' or 'short'
        
    Returns:
        Stop loss price
        
    Example:
        >>> calculate_stop_loss_price(100, 2.0, 'long')
        98.0
    """
    if side == 'long':
        return entry_price * (1 - stop_loss_pct / 100)
    else:  # short
        return entry_price * (1 + stop_loss_pct / 100)


def calculate_take_profit_price(
    entry_price: float,
    take_profit_pct: float,
    side: str = 'long',
) -> float:
    """
    Calculate take profit price from percentage.
    
    Args:
        entry_price: Entry price
        take_profit_pct: Take profit percentage (e.g., 5.0 = 5%)
        side: 'long' or 'short'
        
    Returns:
        Take profit price
        
    Example:
        >>> calculate_take_profit_price(100, 5.0, 'long')
        105.0
    """
    if side == 'long':
        return entry_price * (1 + take_profit_pct / 100)
    else:  # short
        return entry_price * (1 - take_profit_pct / 100)


def should_stop_loss(
    current_price: float,
    entry_price: float,
    stop_loss_pct: float,
    side: str = 'long',
) -> bool:
    """
    Check if stop loss is triggered.
    
    Args:
        current_price: Current market price
        entry_price: Entry price
        stop_loss_pct: Stop loss percentage
        side: 'long' or 'short'
        
    Returns:
        True if stop loss triggered
    """
    stop_price = calculate_stop_loss_price(entry_price, stop_loss_pct, side)
    
    if side == 'long':
        return current_price <= stop_price
    else:  # short
        return current_price >= stop_price


def should_take_profit(
    current_price: float,
    entry_price: float,
    take_profit_pct: float,
    side: str = 'long',
) -> bool:
    """
    Check if take profit is triggered.
    
    Args:
        current_price: Current market price
        entry_price: Entry price
        take_profit_pct: Take profit percentage
        side: 'long' or 'short'
        
    Returns:
        True if take profit triggered
    """
    tp_price = calculate_take_profit_price(entry_price, take_profit_pct, side)
    
    if side == 'long':
        return current_price >= tp_price
    else:  # short
        return current_price <= tp_price


def calculate_trailing_stop_price(
    entry_price: float,
    highest_price: float,
    trailing_pct: float,
    side: str = 'long',
) -> float:
    """
    Calculate trailing stop price.
    
    Args:
        entry_price: Entry price
        highest_price: Highest price since entry
        trailing_pct: Trailing stop percentage
        side: 'long' or 'short'
        
    Returns:
        Trailing stop price
    """
    if side == 'long':
        # Trail from highest price
        return highest_price * (1 - trailing_pct / 100)
    else:  # short
        # Trail from lowest price (highest_price is actually lowest for shorts)
        return highest_price * (1 + trailing_pct / 100)


def calculate_pnl(
    entry_price: float,
    exit_price: float,
    quantity: float,
    side: str = 'long',
) -> Dict[str, float]:
    """
    Calculate realized profit/loss.
    
    Args:
        entry_price: Entry price
        exit_price: Exit price
        quantity: Position quantity
        side: 'long' or 'short'
        
    Returns:
        Dictionary with 'pnl' (absolute) and 'pnl_pct' (percentage)
        
    Example:
        >>> calculate_pnl(100, 105, 10, 'long')
        {'pnl': 50.0, 'pnl_pct': 5.0}
    """
    if side == 'long':
        pnl = (exit_price - entry_price) * quantity
        pnl_pct = ((exit_price / entry_price) - 1) * 100
    else:  # short
        pnl = (entry_price - exit_price) * quantity
        pnl_pct = ((entry_price / exit_price) - 1) * 100
    
    return {
        'pnl': pnl,
        'pnl_pct': pnl_pct,
    }


def calculate_unrealized_pnl(
    entry_price: float,
    current_price: float,
    quantity: float,
    side: str = 'long',
) -> Dict[str, float]:
    """
    Calculate unrealized profit/loss.
    
    Args:
        entry_price: Entry price
        current_price: Current market price
        quantity: Position quantity
        side: 'long' or 'short'
        
    Returns:
        Dictionary with 'unrealized_pnl' and 'unrealized_pnl_pct'
    """
    if side == 'long':
        pnl = (current_price - entry_price) * quantity
        pnl_pct = ((current_price / entry_price) - 1) * 100
    else:  # short
        pnl = (entry_price - current_price) * quantity
        pnl_pct = ((entry_price / current_price) - 1) * 100
    
    return {
        'unrealized_pnl': pnl,
        'unrealized_pnl_pct': pnl_pct,
    }


def calculate_risk_reward_ratio(
    entry_price: float,
    stop_loss_price: float,
    take_profit_price: float,
    side: str = 'long',
) -> float:
    """
    Calculate risk/reward ratio.
    
    Args:
        entry_price: Entry price
        stop_loss_price: Stop loss price
        take_profit_price: Take profit price
        side: 'long' or 'short'
        
    Returns:
        Risk/reward ratio (e.g., 2.0 means 2:1 reward:risk)
        
    Example:
        >>> calculate_risk_reward_ratio(100, 98, 106, 'long')
        # Risk: $2, Reward: $6 = 3:1 ratio
        3.0
    """
    if side == 'long':
        risk = abs(entry_price - stop_loss_price)
        reward = abs(take_profit_price - entry_price)
    else:  # short
        risk = abs(stop_loss_price - entry_price)
        reward = abs(entry_price - take_profit_price)
    
    if risk == 0:
        return 0.0
    
    return reward / risk


def validate_risk_parameters(params: RiskParameters) -> bool:
    """
    Validate risk parameters for sanity.
    
    Args:
        params: Risk parameters to validate
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If parameters are invalid
    """
    if params.position_size_pct <= 0 or params.position_size_pct > 100:
        raise ValueError("Position size % must be between 0 and 100")
    
    if params.stop_loss_pct <= 0:
        raise ValueError("Stop loss % must be positive")
    
    if params.take_profit_pct <= 0:
        raise ValueError("Take profit % must be positive")
    
    if params.max_position_size is not None and params.max_position_size <= 0:
        raise ValueError("Max position size must be positive")
    
    if params.max_daily_trades is not None and params.max_daily_trades <= 0:
        raise ValueError("Max daily trades must be positive")
    
    if params.max_daily_loss_pct is not None and params.max_daily_loss_pct <= 0:
        raise ValueError("Max daily loss % must be positive")
    
    # Check risk/reward ratio
    rr = params.take_profit_pct / params.stop_loss_pct
    if rr < 1.0:
        raise ValueError(
            f"Risk/reward ratio {rr:.2f} is less than 1:1 "
            f"(TP={params.take_profit_pct}%, SL={params.stop_loss_pct}%)"
        )
    
    return True
