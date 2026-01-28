"""Base strategy class for all trading strategies."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from packages.database.db import DatabaseManager
from packages.execution.manager import ExecutionManager
from packages.logging.logger import setup_logger
from packages.signals.types import Signal


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.

    All strategies must inherit from this class and implement:
    - on_candle(): Called when new candle arrives
    - generate_signals(): Generate trading signals from analysis

    The base class provides:
    - Configuration management
    - Database access
    - Execution manager
    - Multi-timeframe candle history
    - Position tracking
    """

    def __init__(
        self,
        config: Dict[str, Any],
        db: DatabaseManager,
        execution_manager: ExecutionManager,
    ):
        """
        Initialize base strategy.

        Args:
            config: Strategy configuration from YAML
            db: Database manager instance
            execution_manager: Execution manager for order placement
        """
        self.config = config
        self.db = db
        self.execution = execution_manager

        # Extract common config values
        self.strategy_id = config["strategy"]["id"]
        self.strategy_name = config["strategy"]["name"]
        self.exchange = config["market"]["exchange"]
        self.symbol = config["market"]["symbol"]
        self.primary_timeframe = config["market"]["primary_timeframe"]
        self.timeframes = config["market"].get("timeframes", [self.primary_timeframe])

        # Strategy parameters (strategy-specific)
        self.parameters = config.get("parameters", {})

        # Candle history storage (keyed by timeframe)
        self.history: Dict[str, List[Dict]] = {tf: [] for tf in self.timeframes}

        # Logger
        self.logger = setup_logger(f"strategy.{self.strategy_id}")
        self.logger.info(
            f"Strategy initialized: {self.strategy_name} "
            f"({self.symbol} on {self.exchange}, {self.primary_timeframe})"
        )

    @abstractmethod
    def on_candle(self, candle: Dict, timeframe: str) -> Optional[Signal]:
        """
        Called when a new candle is received (from WebSocket or backtest).

        This is the main entry point for strategy logic. The strategy should:
        1. Update internal state/history
        2. Analyze market conditions
        3. Generate and return a Signal (or None if no action)

        Args:
            candle: OHLCV candle dict with keys: timestamp, open, high, low, close, volume
            timeframe: Candle timeframe (e.g., '1m', '5m', '1h')

        Returns:
            Signal object if action required, None otherwise
        """
        pass

    @abstractmethod
    def generate_signals(self) -> List[Signal]:
        """
        Generate trading signals from current market state.

        This method should analyze indicators, ML models, order book, etc.
        and return a list of signals from different sources.

        Signals will be aggregated by the strategy aggregator (if configured).

        Returns:
            List of Signal objects from various sources (technical, ML, orderbook)
        """
        pass

    def update_history(self, candle: Dict, timeframe: str, max_candles: int = 500):
        """
        Update candle history for given timeframe.

        Args:
            candle: New candle to add
            timeframe: Timeframe of the candle
            max_candles: Maximum candles to keep in memory
        """
        if timeframe not in self.history:
            self.history[timeframe] = []

        self.history[timeframe].append(candle)

        # Trim history to max length
        if len(self.history[timeframe]) > max_candles:
            self.history[timeframe] = self.history[timeframe][-max_candles:]

    def get_history(self, timeframe: str, periods: int = 50) -> List[Dict]:
        """
        Get recent candle history for timeframe.

        Args:
            timeframe: Timeframe to retrieve
            periods: Number of recent candles to return

        Returns:
            List of recent candles (oldest to newest)
        """
        if timeframe not in self.history:
            return []

        return self.history[timeframe][-periods:]

    def in_position(self) -> bool:
        """Check if currently in a position."""
        return self.execution.position is not None

    def get_position(self):
        """Get current position (or None)."""
        return self.execution.position

    def get_position_summary(self) -> Dict:
        """Get detailed position summary."""
        return self.execution.get_position_summary()

    def log_signal(self, signal: Signal):
        """Log signal to database for analysis."""
        timestamp = signal.timestamp

        self.db.execute(
            """
            INSERT INTO signals (
                strategy_id, exchange, symbol, signal_type, signal_source,
                confidence, reason, metadata, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.strategy_id,
                self.exchange,
                self.symbol,
                signal.type.value,
                signal.source.value,
                signal.confidence,
                signal.reason,
                str(signal.metadata),  # Store as JSON string
                timestamp,
            ),
        )

    def warmup(self, periods: int = 100):
        """
        Load historical candles to warm up indicators.

        Called before strategy starts processing live data.

        Args:
            periods: Number of historical candles to load per timeframe
        """
        self.logger.info(f"Warming up strategy with {periods} candles per timeframe...")

        for timeframe in self.timeframes:
            # Query historical data from database
            rows = self.db.query(
                """
                SELECT timestamp, open, high, low, close, volume
                FROM ohlcv_data
                WHERE exchange = ? AND symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (self.exchange, self.symbol, timeframe, periods),
            )

            # Reverse to get oldest-to-newest order
            candles = [
                {
                    "timestamp": row[0],
                    "open": row[1],
                    "high": row[2],
                    "low": row[3],
                    "close": row[4],
                    "volume": row[5],
                }
                for row in reversed(rows)
            ]

            self.history[timeframe] = candles
            self.logger.info(f"Loaded {len(candles)} candles for {timeframe}")

        self.logger.info("Warmup complete")
