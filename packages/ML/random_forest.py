"""Random Forest based price prediction using feature engineering."""

import pandas as pd
import numpy as np


def calculate_random_forest_prediction(
    df: pd.DataFrame,
    n_estimators: int = 10,
    horizon: int = 3
) -> float:
    """
    Simple Random Forest-style prediction using ensemble of decision rules.
    
    This is a simplified RF implementation. For production,
    use sklearn.ensemble.RandomForestRegressor with proper training.
    
    Args:
        df: Candle data with OHLCV columns
        n_estimators: Number of decision trees (simplified)
        horizon: Number of periods ahead to predict
        
    Returns:
        Predicted price
    """
    if len(df) < 20:
        return df['close'].iloc[-1]
    
    # Feature engineering
    prices = df['close'].tail(50)
    current_price = prices.iloc[-1]
    
    # Create features
    returns = prices.pct_change().fillna(0)
    volatility = returns.rolling(10).std().iloc[-1]
    momentum_5 = (prices.iloc[-1] / prices.iloc[-5]) - 1 if len(prices) >= 5 else 0
    momentum_10 = (prices.iloc[-1] / prices.iloc[-10]) - 1 if len(prices) >= 10 else 0
    
    # Simple decision rules (mimicking decision trees)
    predictions = []
    
    # Tree 1: Momentum-based
    if momentum_5 > 0.02:  # Strong positive momentum
        predictions.append(current_price * 1.01)
    elif momentum_5 < -0.02:  # Strong negative momentum
        predictions.append(current_price * 0.99)
    else:
        predictions.append(current_price)
    
    # Tree 2: Volatility-based
    if volatility > 0.02:  # High volatility
        predictions.append(current_price * 1.005)  # Slight increase
    else:
        predictions.append(current_price * 0.995)  # Slight decrease
    
    # Tree 3: Trend-based
    if momentum_10 > 0:  # Uptrend
        predictions.append(current_price * 1.008)
    else:  # Downtrend
        predictions.append(current_price * 0.992)
    
    # Tree 4: Mean reversion
    mean_price = prices.mean()
    if current_price > mean_price:
        predictions.append(current_price * 0.995)  # Revert down
    else:
        predictions.append(current_price * 1.005)  # Revert up
    
    # Ensemble prediction (average)
    predicted_price = np.mean(predictions)
    
    # Apply horizon multiplier
    price_change = predicted_price - current_price
    predicted_price = current_price + (price_change * horizon)
    
    # Clamp to reasonable bounds (max ±5% move)
    max_move = current_price * 0.05
    predicted_price = np.clip(
        predicted_price,
        current_price - max_move,
        current_price + max_move
    )
    
    return float(predicted_price)
