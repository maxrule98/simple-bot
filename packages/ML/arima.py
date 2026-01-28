"""ARIMA (AutoRegressive Integrated Moving Average) time series prediction."""

import pandas as pd
import numpy as np


def calculate_arima_prediction(
    df: pd.DataFrame,
    order: tuple = (1, 1, 1),
    horizon: int = 3
) -> float:
    """
    Simple ARIMA-style prediction using autoregression.
    
    This is a simplified ARIMA implementation. For production,
    use statsmodels.tsa.arima.model.ARIMA with proper model fitting.
    
    Args:
        df: Candle data with 'close' column
        order: ARIMA order (p, d, q) - default (1,1,1)
        horizon: Number of periods ahead to predict
        
    Returns:
        Predicted price
    """
    if len(df) < 20:
        return df['close'].iloc[-1]
    
    # Get recent prices
    prices = df['close'].tail(30).values
    
    # Apply differencing (I component)
    p, d, q = order
    differenced = prices.copy()
    for _ in range(d):
        differenced = np.diff(differenced)
    
    # Simple AR model (using last p values)
    if len(differenced) >= p:
        # Calculate autoregressive coefficients (simple average)
        ar_component = np.mean([differenced[-i] for i in range(1, p+1)])
    else:
        ar_component = differenced[-1]
    
    # Predict next value
    predicted_diff = ar_component
    
    # Reverse differencing to get price
    current_price = prices[-1]
    predicted_price = current_price + predicted_diff * horizon
    
    # Clamp to reasonable bounds (max ±5% move)
    max_move = current_price * 0.05
    predicted_price = np.clip(
        predicted_price,
        current_price - max_move,
        current_price + max_move
    )
    
    return float(predicted_price)
