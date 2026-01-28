"""Generic YAML-driven strategy."""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

from packages.strategies.base import BaseStrategy
from packages.strategies.condition_evaluator import ConditionEvaluator
from packages.signals.types import Signal, SignalType, SignalSource
from packages.database.db import DatabaseManager
from packages.execution.manager import ExecutionManager
from packages.indicators import calculate_rsi, calculate_sma, calculate_ema
from packages.ML import (
    calculate_price_prediction,
    calculate_arima_prediction,
    calculate_random_forest_prediction
)


class YAMLStrategy(BaseStrategy):
    """
    Generic strategy driven by YAML configuration.
    
    No hardcoded logic - all entry/exit conditions from config.
    """
    
    def __init__(
        self,
        config: Dict,
        db: DatabaseManager,
        execution_manager: ExecutionManager
    ):
        """
        Initialize YAML strategy.
        
        Args:
            config: Full strategy configuration dict
            db: Database manager
            execution_manager: Execution manager
        """
        super().__init__(config, db, execution_manager)
        
        # Extract entry/exit conditions
        self.entry_conditions = config.get('entry', {}).get('conditions', [])
        self.exit_conditions = config.get('exit', {}).get('conditions', [])
        self.condition_mode = config.get('entry', {}).get('mode', 'AND')  # AND/OR
        
        # Extract indicator configs
        self.indicator_configs = config.get('indicators', [])
        
        # Track calculated indicators
        self.indicators: Dict[str, float] = {}
        
    def on_candle(self, candle: Dict, timeframe: str) -> None:
        """
        Process new candle and generate signals.
        
        Args:
            candle: New candle data
            timeframe: Candle timeframe
        """
        # Update history
        self.update_history(candle, timeframe)
        
        # Get history for primary timeframe
        history = self.history.get(self.primary_timeframe, [])
        if len(history) < 2:
            return  # Need at least 2 candles
        
        # Calculate indicators
        self._calculate_indicators(history)
        
        # Generate signals
        signals = self.generate_signals(candle)
        
        # Log and execute signals
        for signal in signals:
            self.log_signal(signal)
            self.execution.execute_signal(signal, self.symbol, float(candle['close']))
    
    def generate_signals(self, candle: Dict) -> List[Signal]:
        """
        Generate signals based on YAML conditions.
        
        Args:
            candle: Current candle
            
        Returns:
            List of signals
        """
        signals = []
        
        # Build context
        context = self._build_context(candle)
        
        # Create evaluator
        evaluator = ConditionEvaluator(self.indicators, context)
        
        # Check entry conditions (if not in position)
        if not self.in_position():
            if evaluator.evaluate_all(self.entry_conditions, mode=self.condition_mode):
                confidence = self._calculate_confidence(evaluator, self.entry_conditions)
                reason = self._format_reason(self.entry_conditions, self.indicators, context)
                
                signals.append(Signal(
                    type=SignalType.BUY,
                    source=SignalSource.TECHNICAL,
                    confidence=confidence,
                    reason=reason,
                    metadata={
                        'conditions': self.entry_conditions,
                        'indicators': self.indicators.copy(),
                        'context': context.copy()
                    },
                    timestamp=candle['timestamp']
                ))
        
        # Check exit conditions (if in position)
        else:
            if evaluator.evaluate_all(self.exit_conditions, mode="OR"):  # Any exit triggers
                reason = self._format_reason(self.exit_conditions, self.indicators, context)
                
                signals.append(Signal(
                    type=SignalType.CLOSE,  # Close position, not open short
                    source=SignalSource.TECHNICAL,
                    confidence=1.0,
                    reason=reason,
                    metadata={
                        'conditions': self.exit_conditions,
                        'indicators': self.indicators.copy(),
                        'context': context.copy()
                    },
                    timestamp=candle['timestamp']
                ))
        
        return signals
    
    def _calculate_indicators(self, history: List[Dict]) -> None:
        """
        Calculate all indicators from config.
        
        Args:
            history: Candle history
        """
        # Convert to DataFrame for easier calculation
        df = pd.DataFrame(history)
        
        # Calculate each indicator
        for indicator_config in self.indicator_configs:
            name = indicator_config['name']
            params = indicator_config.get('params', {})
            
            if name == "RSI":
                self.indicators['RSI'] = calculate_rsi(df, params.get('period', 14))
            elif name == "SMA":
                self.indicators['SMA'] = calculate_sma(df, params.get('period', 20))
            elif name == "EMA":
                self.indicators['EMA'] = calculate_ema(df, params.get('period', 20))
            elif name == "PRICE_PREDICTION":
                self.indicators['PRICE_PREDICTION'] = calculate_price_prediction(
                    df, 
                    lookback=params.get('lookback', 10),
                    horizon=params.get('horizon', 3)
                )
            elif name == "ARIMA_PREDICTION":
                self.indicators['ARIMA_PREDICTION'] = calculate_arima_prediction(
                    df,
                    order=tuple(params.get('order', [1, 1, 1])),
                    horizon=params.get('horizon', 3)
                )
            elif name == "RF_PREDICTION":
                self.indicators['RF_PREDICTION'] = calculate_random_forest_prediction(
                    df,
                    n_estimators=params.get('n_estimators', 10),
                    horizon=params.get('horizon', 3)
                )
            # TODO: Add more indicators (MACD, Bollinger Bands, ATR, etc.)
    
    def _build_context(self, candle: Dict) -> Dict[str, float]:
        """
        Build context variables for condition evaluation.
        
        Args:
            candle: Current candle
            
        Returns:
            Context dict with variables like PRICE, PNL_PCT, etc.
        """
        context = {
            'PRICE': float(candle['close']),
            'VOLUME': float(candle['volume']),
        }
        
        # Add position context if in position
        position = self.get_position()
        if position:
            pnl_pct = ((float(candle['close']) - position.entry_price) / position.entry_price) * 100
            context['PNL_PCT'] = pnl_pct
            context['POSITION_SIZE'] = position.quantity
            context['ENTRY_PRICE'] = position.entry_price
        
        return context
    
    def _calculate_confidence(self, evaluator: ConditionEvaluator, conditions: List[str]) -> float:
        """
        Calculate signal confidence based on condition satisfaction.
        
        Args:
            evaluator: Condition evaluator
            conditions: List of conditions
            
        Returns:
            Confidence score (0.0 - 1.0)
        """
        if not conditions:
            return 0.0
        
        # Count how many conditions are satisfied
        satisfied = sum(1 for cond in conditions if evaluator.evaluate(cond))
        
        return satisfied / len(conditions)
    
    def _format_reason(
        self,
        conditions: List[str],
        indicators: Dict[str, float],
        context: Dict[str, float]
    ) -> str:
        """
        Format human-readable reason for signal.
        
        Args:
            conditions: List of conditions
            indicators: Current indicator values
            context: Current context values
            
        Returns:
            Formatted reason string
        """
        parts = []
        
        # Add indicator values
        for name, value in indicators.items():
            parts.append(f"{name}={value:.1f}")
        
        # Add key context
        if 'PNL_PCT' in context:
            parts.append(f"PNL={context['PNL_PCT']:.1f}%")
        
        # Add first satisfied condition
        for cond in conditions:
            evaluator = ConditionEvaluator(indicators, context)
            if evaluator.evaluate(cond):
                parts.append(f"({cond})")
                break
        
        return ", ".join(parts)
