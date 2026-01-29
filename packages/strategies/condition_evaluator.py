"""Condition evaluator for YAML-driven strategies."""

import re
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np


class ConditionEvaluator:
    """
    Evaluates YAML condition strings against market context.
    
    Supports comparisons:
    - RSI < 30
    - MACD_HIST > 0
    - PRICE > VWAP
    - PNL_PCT < -1.0
    
    Operators: <, >, <=, >=, ==, !=
    Logical operators: AND, OR
    """
    
    OPERATORS = {
        '<': lambda a, b: a < b,
        '>': lambda a, b: a > b,
        '<=': lambda a, b: a <= b,
        '>=': lambda a, b: a >= b,
        '==': lambda a, b: a == b,
        '!=': lambda a, b: a != b,
    }
    
    def __init__(self, indicators: Dict[str, Any], context: Optional[Dict[str, Any]] = None):
        """
        Initialize evaluator with available indicators and context.
        
        Args:
            indicators: Dict of indicator_name -> current_value or Series
            context: Additional context (position, pnl, price, etc.)
        """
        self.indicators = indicators
        self.context = context or {}
        self.data = None
        
    def evaluate(self, condition: str, data: Optional[Dict[str, pd.Series]] = None) -> Union[bool, pd.Series]:
        """
        Evaluate a condition string.
        
        Args:
            condition: Condition string (e.g., "RSI < 30" or "RSI < 30 AND PRICE > SMA")
            data: Optional DataFrame columns for element-wise evaluation
            
        Returns:
            If data provided: pandas Series of bool values (element-wise evaluation)
            If no data: bool value (scalar evaluation)
        """
        self.data = data
        
        # Handle AND/OR operators
        if ' AND ' in condition:
            parts = condition.split(' AND ')
            result = self.evaluate(parts[0].strip(), data)
            for part in parts[1:]:
                part_result = self.evaluate(part.strip(), data)
                result = result & part_result if isinstance(result, pd.Series) else (result and part_result)
            return result
        
        if ' OR ' in condition:
            parts = condition.split(' OR ')
            result = self.evaluate(parts[0].strip(), data)
            for part in parts[1:]:
                part_result = self.evaluate(part.strip(), data)
                result = result | part_result if isinstance(result, pd.Series) else (result or part_result)
            return result
        
        # Parse simple condition
        match = re.match(r'^\s*([A-Za-z_]+[A-Za-z0-9_]*)\s*([<>=!]+)\s*(.+)\s*$', condition.strip())
        if not match:
            raise ValueError(f"Invalid condition format: {condition}")
        
        left_var = match.group(1)
        operator = match.group(2)
        right_value = match.group(3).strip()
        
        # Get left value
        left_val = self._get_value(left_var)
        if left_val is None:
            if self.data:
                # Return Series of False with same length as data
                length = len(next(iter(self.data.values())))
                return pd.Series([False] * length)
            return False
        
        # Get right value
        right_val = self._get_value(right_value)
        if right_val is None:
            if self.data:
                length = len(next(iter(self.data.values())))
                return pd.Series([False] * length)
            return False
        
        # Evaluate comparison
        if operator not in self.OPERATORS:
            raise ValueError(f"Unsupported operator: {operator}")
        
        return self.OPERATORS[operator](left_val, right_val)
    
    def evaluate_all(self, conditions: List[str], mode: str = "AND") -> bool:
        """
        Evaluate multiple conditions.
        
        Args:
            conditions: List of condition strings
            mode: "AND" (all must be true) or "OR" (any must be true)
            
        Returns:
            True if conditions satisfied, False otherwise
        """
        if not conditions:
            return False
        
        results = [self.evaluate(cond) for cond in conditions]
        
        # Support both uppercase (AND/OR) and intuitive aliases (ALL/ANY)
        mode_upper = mode.upper()
        if mode_upper in ("AND", "ALL"):
            return all(results)
        elif mode_upper in ("OR", "ANY"):
            return any(results)
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'AND'/'ALL' or 'OR'/'ANY'.")
    
    def _get_value(self, var: str) -> Any:
        """
        Get value for a variable (indicator, context, or literal).
        
        Args:
            var: Variable name or literal value
            
        Returns:
            Variable value (scalar, Series, or parsed literal)
        """
        # Check if it's a literal number
        try:
            return float(var)
        except ValueError:
            pass
        
        # Check if it's a literal string
        if var.startswith('"') or var.startswith("'"):
            return var.strip('"\'')
        
        # Check data (Series) first if data provided
        if self.data and var in self.data:
            return self.data[var]
        
        # Check indicators
        if var in self.indicators:
            value = self.indicators[var]
            # If we have data context, try to get from data instead
            if self.data and var in self.data:
                return self.data[var]
            return value
        
        # Check context
        if var in self.context:
            value = self.context[var]
            # If we have data context, try to get from data instead
            if self.data and var in self.data:
                return self.data[var]
            return value
        
        # Not found
        return None
