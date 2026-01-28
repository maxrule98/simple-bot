"""EMA (Exponential Moving Average) indicator."""

import pandas as pd


def calculate_ema(df: pd.DataFrame, period: int = 20) -> float:
    """
    Calculate Exponential Moving Average.
    
    Args:
        df: Candle data with 'close' column
        period: EMA period (default: 20)
        
    Returns:
        Current EMA value
    """
    if len(df) < period:
        return df['close'].mean()  # Fallback to available data average
    
    ema = df['close'].ewm(span=period, adjust=False).mean()
    return float(ema.iloc[-1])
