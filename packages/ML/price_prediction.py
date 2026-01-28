"""Simple price prediction indicator using momentum."""

import pandas as pd
import numpy as np


def calculate_price_prediction(df: pd.DataFrame, lookback: int = 10, horizon: int = 3) -> float:
    """
    Simple ML-style price prediction using momentum and trend.
    
    Predicts future price by analyzing recent price momentum and volatility.
    This is a simplified ML indicator - can be replaced with actual LSTM/ARIMA models.
    
    Args:
        df: Candle data with 'close' column
        lookback: Number of periods to analyze (default: 10)
        horizon: Number of periods ahead to predict (default: 3)
        
    Returns:
        Predicted price
    """
    if len(df) < lookback + 5:
        return df['close'].iloc[-1]  # Not enough data
    
    # Get recent prices
    recent_prices = df['close'].tail(lookback)
    current_price = recent_prices.iloc[-1]
    
    # Calculate momentum (rate of change)
    momentum = recent_prices.pct_change().mean()
    
    # Calculate volatility (standard deviation of returns)
    volatility = recent_prices.pct_change().std()
    
    # Calculate trend strength using linear regression slope
    x = np.arange(len(recent_prices))
    y = recent_prices.values
    trend = np.polyfit(x, y, 1)[0]  # Slope of linear fit
    
    # Weight factors
    # - Stronger momentum = larger price change expected
    # - Higher trend = continuation expected
    # - Adjust for volatility (more volatile = less confident)
    
    momentum_component = current_price * momentum * horizon
    trend_component = trend * horizon
    volatility_adjustment = 1 - (volatility * 0.5)  # Reduce confidence in volatile markets
    
    # Predicted price
    predicted_price = current_price + (momentum_component + trend_component) * volatility_adjustment
    
    # Clamp to reasonable bounds (max ±10% move)
    max_move = current_price * 0.10
    predicted_price = np.clip(predicted_price, current_price - max_move, current_price + max_move)
    
    return float(predicted_price)
