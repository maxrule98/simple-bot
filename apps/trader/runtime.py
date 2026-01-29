"""Trading runtime - connects WebSocket → Strategy → Execution."""

import asyncio
import os
import signal as sys_signal
from typing import Dict

from dotenv import load_dotenv

from packages.database.db import DatabaseManager
from packages.execution.manager import ExecutionManager
from packages.logging.logger import setup_logger
from packages.strategies.base import BaseStrategy
from packages.strategies.loader import StrategyLoader
from packages.websocket.websocket import WebSocketManager
from apps.backfiller.main import Backfiller

# Load environment variables from .env file
load_dotenv()


class TradingRuntime:
    """
    Main trading loop that orchestrates:
    1. WebSocket data streaming (OHLCV, ticker, trades, orderbook)
    2. Strategy signal generation
    3. Order execution

    This is the core runtime for live and paper trading.
    """

    def __init__(
        self,
        config_path: str,
        mode: str = "paper",
        api_key: str = None,
        api_secret: str = None,
    ):
        """
        Initialize trading runtime.

        Args:
            config_path: Path to strategy YAML config
            mode: Trading mode ('live' or 'paper')
            api_key: Exchange API key (from env or passed directly)
            api_secret: Exchange API secret (from env or passed directly)
        """
        self.config_path = config_path
        self.mode = mode
        self.logger = setup_logger(f"runtime.{mode}")

        # API credentials will be loaded based on exchange from config
        self.api_key = api_key
        self.api_secret = api_secret

        # Initialize components (will be set in setup)
        self.db: DatabaseManager = None
        self.execution: ExecutionManager = None
        self.strategy: BaseStrategy = None
        self.websocket: WebSocketManager = None

        # Shutdown flag
        self.running = False

        self.logger.info(f"TradingRuntime initialized (mode={mode})")

    async def setup(self):
        """Initialize all components."""
        self.logger.info("Setting up trading runtime...")

        # Load strategy config
        config = StrategyLoader.load_config(self.config_path)
        strategy_id = config["strategy"]["id"]
        exchange = config["market"]["exchange"]
        symbol = config["market"]["symbol"]
        timeframes = config["market"].get("timeframes", [config["market"]["primary_timeframe"]])

        # Load API credentials for this exchange
        if self.api_key is None:
            self.api_key = os.getenv(f"{exchange.upper()}_API_KEY")
        if self.api_secret is None:
            self.api_secret = os.getenv(f"{exchange.upper()}_API_SECRET")

        if not self.api_key or not self.api_secret:
            raise ValueError(
                f"API credentials required for {exchange} "
                f"(set {exchange.upper()}_API_KEY and {exchange.upper()}_API_SECRET in .env)"
            )

        # Initialize database
        db_path = os.getenv("DATABASE_PATH", "data/trading.db")
        self.db = DatabaseManager(db_path)
        self.logger.info(f"Connected to database: {db_path}")

        # Backfill historical data before strategy warmup
        self.logger.info(f"Backfilling historical data for {symbol}...")
        try:
            backfiller = Backfiller(exchange)
            for timeframe in timeframes:
                await backfiller.backfill(symbol, timeframe)
            self.logger.info("✅ Backfill complete")
        except Exception as e:
            self.logger.warning(f"⚠️ Backfill failed (non-critical): {e}")
            self.logger.info("Proceeding with warmup using existing database data...")

        # Initialize execution manager
        self.execution = ExecutionManager(
            exchange_name=exchange,
            api_key=self.api_key,
            api_secret=self.api_secret,
            db=self.db,
            strategy_id=strategy_id,
            mode=self.mode,
        )

        # Load strategy
        self.strategy = StrategyLoader.load_strategy(config, self.db, self.execution)

        # Warm up strategy with historical data
        self.strategy.warmup(periods=100)

        # Initialize WebSocket manager
        self.websocket = WebSocketManager(
            exchange_name=exchange,
            symbols=[symbol],
            db_connection=self.db,
            orderbook_depth=10,
        )

        # Connect to WebSocket
        await self.websocket.connect()
        
        # Register candle callback
        self.websocket.register_candle_callback(self._on_candle)

        self.logger.info(f"Setup complete: {strategy_id} on {symbol} ({exchange})")

    async def _on_candle(self, candle: Dict, timeframe: str):
        """
        Callback when new candle received from WebSocket.

        Args:
            candle: OHLCV candle dict
            timeframe: Candle timeframe
        """
        symbol = self.strategy.symbol
        current_price = candle["close"]

        # Update strategy history
        self.strategy.update_history(candle, timeframe)

        # Update position PNL if in position
        if self.strategy.in_position():
            self.execution.update_position_pnl(current_price)

        # Generate signal from strategy
        try:
            signal = self.strategy.on_candle(candle, timeframe)

            if signal is not None:
                self.logger.info(f"Signal generated: {signal}")

                # Log signal to database
                self.strategy.log_signal(signal)

                # Execute signal
                success = self.execution.execute_signal(signal, symbol, current_price)

                if success:
                    self.logger.info(f"Signal executed successfully")
                else:
                    self.logger.warning(f"Signal execution failed")

        except Exception as e:
            self.logger.error(f"Error processing candle: {e}", exc_info=True)

    async def run(self):
        """Start the trading runtime."""
        self.logger.info("=" * 60)
        self.logger.info(f"Starting trading runtime in {self.mode.upper()} mode")
        self.logger.info("=" * 60)

        self.running = True

        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (sys_signal.SIGINT, sys_signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        try:
            # Start WebSocket streams
            symbol = self.strategy.symbol
            timeframes = self.strategy.timeframes

            # Set running flag
            self.websocket.running = True

            tasks = []

            # Watch OHLCV for all timeframes
            for tf in timeframes:
                tasks.append(self.websocket.watch_ohlcv(symbol, tf))

            # Watch ticker (for position PNL updates)
            tasks.append(self.websocket.watch_ticker(symbol))

            # Watch trades (for True VWAP calculation)
            tasks.append(self.websocket.watch_trades(symbol))

            # Watch order book (for orderbook signals)
            tasks.append(self.websocket.watch_order_book(symbol))

            self.logger.info(f"WebSocket streams started for {symbol}")
            self.logger.info(f"Monitoring timeframes: {timeframes}")
            self.logger.info("Press Ctrl+C to stop")

            # Run all streams concurrently
            await asyncio.gather(*tasks)

        except asyncio.CancelledError:
            self.logger.info("Runtime cancelled")
        except Exception as e:
            self.logger.error(f"Runtime error: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def shutdown(self):
        """Graceful shutdown."""
        if not self.running:
            return

        self.logger.info("Shutting down trading runtime...")
        self.running = False

        # Close any open positions (optional - for safety)
        if self.strategy and self.strategy.in_position():
            self.logger.warning("Open position detected - consider manual close")
            position = self.strategy.get_position_summary()
            self.logger.info(f"Position: {position}")

        # Close WebSocket connections
        if self.websocket:
            await self.websocket.stop()

        # Close database
        if self.db:
            self.db.close()

        self.logger.info("Shutdown complete")


async def main():
    """Entry point for trading runtime."""
    import argparse

    parser = argparse.ArgumentParser(description="Trading Runtime")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to strategy config YAML",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="paper",
        choices=["live", "paper"],
        help="Trading mode (default: paper)",
    )

    args = parser.parse_args()

    # Initialize and run runtime
    runtime = TradingRuntime(config_path=args.config, mode=args.mode)
    await runtime.setup()
    await runtime.run()


if __name__ == "__main__":
    asyncio.run(main())
