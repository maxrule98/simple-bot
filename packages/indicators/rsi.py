"""RSI (Relative Strength Index) indicator."""

import pandas as pd


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> float:
    """
    Calculate RSI indicator.
    
    Args:
        df: Candle data with 'close' column
        period: RSI period (default: 14)
        
    Returns:
        Current RSI value (0-100)
    """
    if len(df) < period + 1:
        return 50.0  # Neutral if not enough data
    
    # Calculate price changes
    delta = df['close'].diff()
    
    # Separate gains and losses
    gains = delta.where(delta > 0, 0.0)
    losses = -delta.where(delta < 0, 0.0)
    
    # Calculate average gains and losses
    avg_gains = gains.rolling(window=period).mean()
    avg_losses = losses.rolling(window=period).mean()
    
    # Calculate RS and RSI
    rs = avg_gains / avg_losses
    rsi = 100 - (100 / (1 + rs))
    
    return float(rsi.iloc[-1])
