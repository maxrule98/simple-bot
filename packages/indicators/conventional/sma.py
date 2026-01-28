"""SMA (Simple Moving Average) indicator."""

import pandas as pd


def calculate_sma(df: pd.DataFrame, period: int = 20) -> float:
    """
    Calculate Simple Moving Average.
    
    Args:
        df: Candle data with 'close' column
        period: SMA period (default: 20)
        
    Returns:
        Current SMA value
    """
    if len(df) < period:
        return df['close'].mean()  # Fallback to available data average
    
    sma = df['close'].rolling(window=period).mean()
    return float(sma.iloc[-1])
