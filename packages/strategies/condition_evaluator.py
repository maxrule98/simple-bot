"""Condition evaluator for YAML-driven strategies."""

import re
from typing import Any, Dict, List


class ConditionEvaluator:
    """
    Evaluates YAML condition strings against market context.
    
    Supports comparisons:
    - RSI < 30
    - MACD_HIST > 0
    - PRICE > VWAP
    - PNL_PCT < -1.0
    
    Operators: <, >, <=, >=, ==, !=
    """
    
    OPERATORS = {
        '<': lambda a, b: a < b,
        '>': lambda a, b: a > b,
        '<=': lambda a, b: a <= b,
        '>=': lambda a, b: a >= b,
        '==': lambda a, b: a == b,
        '!=': lambda a, b: a != b,
    }
    
    def __init__(self, indicators: Dict[str, Any], context: Dict[str, Any]):
        """
        Initialize evaluator with available indicators and context.
        
        Args:
            indicators: Dict of indicator_name -> current_value
            context: Additional context (position, pnl, price, etc.)
        """
        self.indicators = indicators
        self.context = context
        
    def evaluate(self, condition: str) -> bool:
        """
        Evaluate a condition string.
        
        Args:
            condition: Condition string (e.g., "RSI < 30")
            
        Returns:
            True if condition is satisfied, False otherwise
        """
        # Parse condition
        match = re.match(r'^\s*([A-Z_]+)\s*([<>=!]+)\s*(.+)\s*$', condition)
        if not match:
            raise ValueError(f"Invalid condition format: {condition}")
        
        left_var = match.group(1)
        operator = match.group(2)
        right_value = match.group(3).strip()
        
        # Get left value
        left_val = self._get_value(left_var)
        if left_val is None:
            return False  # Variable not available
        
        # Get right value
        right_val = self._get_value(right_value)
        
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
        
        if mode == "AND":
            return all(results)
        elif mode == "OR":
            return any(results)
        else:
            raise ValueError(f"Invalid mode: {mode}")
    
    def _get_value(self, var: str) -> Any:
        """
        Get value for a variable (indicator, context, or literal).
        
        Args:
            var: Variable name or literal value
            
        Returns:
            Variable value or parsed literal
        """
        # Check if it's a literal number
        try:
            return float(var)
        except ValueError:
            pass
        
        # Check if it's a literal string
        if var.startswith('"') or var.startswith("'"):
            return var.strip('"\'')
        
        # Check indicators
        if var in self.indicators:
            return self.indicators[var]
        
        # Check context
        if var in self.context:
            return self.context[var]
        
        # Not found
        return None
