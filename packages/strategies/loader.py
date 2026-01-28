"""Strategy loader for dynamic YAML-based strategy instantiation."""

import importlib
import os
from pathlib import Path
from typing import Any, Dict

import yaml

from packages.database.db import DatabaseManager
from packages.execution.manager import ExecutionManager
from packages.logging.logger import setup_logger
from packages.strategies.base import BaseStrategy

logger = setup_logger("strategy_loader")


class StrategyLoader:
    """
    Dynamically loads strategy classes from YAML configuration.

    YAML-First Approach:
    - Simple strategies: Define conditions in YAML (no Python code)
    - Complex strategies: Create Python class and specify module path

    Example YAML (simple strategy, uses YAMLStrategy):
        strategy:
          id: "btc-rsi-001"
          name: "BTC RSI Strategy"
          # No "class" field = uses YAMLStrategy

        indicators:
          - name: "RSI"
            params:
              period: 14

        entry:
          conditions:
            - "RSI < 30"

        exit:
          conditions:
            - "RSI > 70"

    Example YAML (custom Python strategy):
        strategy:
          id: "advanced-ml-001"
          name: "Advanced ML Strategy"
          class: "AdvancedMLStrategy"
          module: "advanced_ml_strategy"  # packages/strategies/advanced_ml_strategy.py

        market:
          exchange: "mexc"
          symbol: "BTC/USDT"
          primary_timeframe: "1m"
    """

    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        """
        Load strategy configuration from YAML file.

        Args:
            config_path: Path to YAML config file

        Returns:
            Dictionary with strategy configuration

        Raises:
            FileNotFoundError: If config file not found
            yaml.YAMLError: If YAML parsing fails
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        logger.info(f"Loaded config: {config_path}")
        return config

    @staticmethod
    def load_strategy(
        config: Dict[str, Any],
        db: DatabaseManager,
        execution_manager: ExecutionManager,
    ) -> BaseStrategy:
        """
        Load and instantiate strategy from configuration.

        Args:
            config: Strategy configuration dictionary
            db: Database manager instance
            execution_manager: Execution manager instance

        Returns:
            Instantiated strategy object

        Raises:
            ValueError: If strategy class not found
            ImportError: If strategy module import fails
        """
        # Check if YAML-only strategy (no Python class specified)
        strategy_class_name = config["strategy"].get("class")
        
        if strategy_class_name is None:
            # Use generic YAMLStrategy
            from packages.strategies.yaml_strategy import YAMLStrategy
            
            strategy = YAMLStrategy(
                config=config, db=db, execution_manager=execution_manager
            )
            logger.info(
                f"Loaded YAML-driven strategy: {config['strategy']['name']}"
            )
            return strategy
        
        # Load custom Python strategy class
        module_path = config["strategy"].get("module")

        # If no module path provided, search in conventional/ and custom/
        if module_path is None:
            module_path = StrategyLoader._find_strategy_module(strategy_class_name)

        # Import strategy module
        try:
            full_module_path = f"packages.strategies.{module_path}"
            module = importlib.import_module(full_module_path)
            logger.info(f"Imported module: {full_module_path}")
        except ImportError as e:
            raise ImportError(
                f"Failed to import strategy module '{full_module_path}': {e}"
            )

        # Get strategy class
        if not hasattr(module, strategy_class_name):
            raise ValueError(
                f"Strategy class '{strategy_class_name}' not found in module '{full_module_path}'"
            )

        strategy_class = getattr(module, strategy_class_name)

        # Instantiate strategy
        strategy = strategy_class(
            config=config, db=db, execution_manager=execution_manager
        )

        logger.info(
            f"Loaded strategy: {config['strategy']['name']} ({strategy_class_name})"
        )

        return strategy

    @staticmethod
    def _find_strategy_module(class_name: str) -> str:
        """
        Search for strategy module by class name.

        Note: For complex strategies requiring custom Python code,
        create a module in packages/strategies/ and specify the
        module path in YAML config:
        
            strategy:
              class: "MyComplexStrategy"
              module: "my_complex_strategy"  # packages/strategies/my_complex_strategy.py

        For simple strategies, omit the "class" field to use YAMLStrategy.

        Args:
            class_name: Strategy class name (PascalCase)

        Returns:
            Module name (without packages.strategies. prefix)

        Raises:
            ValueError: Strategy module must be explicitly specified in config
        """
        raise ValueError(
            f"Custom strategy class '{class_name}' requires explicit module path in config.\n"
            f"Add to your YAML config:\n"
            f"  strategy:\n"
            f"    class: \"{class_name}\"\n"
            f"    module: \"your_module_name\"  # e.g., 'my_strategy' for packages/strategies/my_strategy.py\n\n"
            f"Or for simple strategies, remove the 'class' field to use YAML-driven YAMLStrategy."
        )

    @staticmethod
    def load_from_file(
        config_path: str,
        db: DatabaseManager,
        execution_manager: ExecutionManager,
    ) -> BaseStrategy:
        """
        Convenience method to load config and strategy in one call.

        Args:
            config_path: Path to YAML config file
            db: Database manager instance
            execution_manager: Execution manager instance

        Returns:
            Instantiated strategy object
        """
        config = StrategyLoader.load_config(config_path)
        strategy = StrategyLoader.load_strategy(config, db, execution_manager)
        return strategy
