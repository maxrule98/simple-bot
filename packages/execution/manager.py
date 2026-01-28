"""Execution manager for order placement and position tracking."""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

import ccxt

from packages.database.db import DatabaseManager
from packages.logging.logger import setup_logger
from packages.signals.types import Signal, SignalType


class OrderStatus(Enum):
    """Order lifecycle status."""

    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class Position:
    """
    Current trading position.

    Attributes:
        symbol: Trading pair (e.g., 'BTC/USDT')
        side: 'long' or 'short'
        entry_price: Average entry price
        quantity: Position size (in base currency)
        entry_time: Entry timestamp (milliseconds)
        unrealized_pnl: Current unrealized profit/loss
        highest_price: Highest price since entry (for trailing stops)
    """

    symbol: str
    side: str
    entry_price: float
    quantity: float
    entry_time: int
    unrealized_pnl: float = 0.0
    highest_price: float = 0.0


class ExecutionManager:
    """
    Handles order execution and position tracking.

    Responsibilities:
    - Place market/limit orders via exchange API
    - Track open positions
    - Calculate PNL (realized and unrealized)
    - Switch between live and paper trading modes
    - Store trades in database
    """

    def __init__(
        self,
        exchange_name: str,
        api_key: str,
        api_secret: str,
        db: DatabaseManager,
        strategy_id: str,
        mode: str = "paper",
    ):
        """
        Initialize execution manager.

        Args:
            exchange_name: Exchange name (e.g., 'mexc', 'binance')
            api_key: API key
            api_secret: API secret
            db: Database manager instance
            strategy_id: Unique strategy identifier
            mode: 'live' or 'paper' trading mode
        """
        self.exchange_name = exchange_name
        self.db = db
        self.strategy_id = strategy_id
        self.mode = mode
        self.logger = setup_logger(f"execution.{strategy_id}")

        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_name)
        self.exchange = exchange_class(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
            }
        )

        # Paper mode uses simulated execution (no real orders)
        if mode == "paper":
            self.logger.info(f"Initialized {exchange_name} in PAPER mode (simulated execution)")
            self.logger.warning("Paper mode: Orders will be simulated, not sent to exchange")
        else:
            self.logger.warning(f"Initialized {exchange_name} in LIVE mode - REAL MONEY!")

        # Position tracking
        self.position: Optional[Position] = None

        self.logger.info(f"ExecutionManager initialized (mode={mode})")

    def execute_signal(self, signal: Signal, symbol: str, current_price: float) -> bool:
        """
        Execute a trading signal.

        Args:
            signal: Signal object to execute
            symbol: Trading pair
            current_price: Current market price

        Returns:
            True if execution successful, False otherwise
        """
        try:
            if signal.type == SignalType.BUY:
                return self._execute_buy(signal, symbol, current_price)
            elif signal.type == SignalType.SELL:
                return self._execute_sell(signal, symbol, current_price)
            elif signal.type == SignalType.CLOSE:
                return self._execute_close(signal, symbol, current_price)
            elif signal.type == SignalType.PARTIAL_CLOSE:
                return self._execute_partial_close(signal, symbol, current_price)
            else:
                self.logger.error(f"Unknown signal type: {signal.type}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to execute signal {signal}: {e}", exc_info=True)
            return False

    def _execute_buy(self, signal: Signal, symbol: str, current_price: float) -> bool:
        """Execute BUY signal (open long position)."""
        if self.position is not None:
            self.logger.warning("Already in position, ignoring BUY signal")
            return False

        # TODO: Get position size from strategy config (for now, hardcode small amount)
        # In production, this should be calculated based on:
        # - Account balance
        # - Risk percentage (e.g., 2% of account)
        # - Stop loss distance
        quantity = 0.001  # Small test amount (0.001 BTC)

        self.logger.info(
            f"Executing BUY: {quantity} {symbol} @ {current_price} "
            f"(confidence={signal.confidence:.2f}, reason={signal.reason})"
        )

        # Place market buy order (or simulate in paper mode)
        if self.mode == "paper":
            # Simulated execution
            import time
            order = {
                "id": f"sim_{int(time.time() * 1000)}",
                "timestamp": int(time.time() * 1000),
                "status": "closed",
                "symbol": symbol,
                "type": "market",
                "side": "buy",
                "price": current_price,
                "amount": quantity,
                "filled": quantity,
                "remaining": 0,
            }
            self.logger.info(f"Order simulated: {order['id']}")
        else:
            # Real execution
            order = self.exchange.create_market_buy_order(symbol, quantity)
            self.logger.info(f"Order placed: {order['id']}")

        # Create position
        self.position = Position(
            symbol=symbol,
            side="long",
            entry_price=current_price,  # Simplified (should use fill price)
            quantity=quantity,
            entry_time=int(time.time() * 1000),
            highest_price=current_price,
        )

        # Store trade in database
        self._store_trade(
            symbol=symbol,
            side="buy",
            price=current_price,
            quantity=quantity,
            signal=signal,
            order_id=order["id"],
        )

        return True

    def _execute_sell(self, signal: Signal, symbol: str, current_price: float) -> bool:
        """Execute SELL signal (open short position)."""
        # TODO: Implement short selling (requires margin/futures)
        self.logger.warning("Short selling not yet implemented")
        return False

    def _execute_close(self, signal: Signal, symbol: str, current_price: float) -> bool:
        """Execute CLOSE signal (close entire position)."""
        if self.position is None:
            self.logger.warning("No position to close")
            return False

        self.logger.info(
            f"Executing CLOSE: {self.position.quantity} {symbol} @ {current_price} "
            f"(entry={self.position.entry_price}, reason={signal.reason})"
        )

        # Place market sell order (or simulate in paper mode)
        if self.mode == "paper":
            # Simulated execution
            import time
            order = {
                "id": f"sim_{int(time.time() * 1000)}",
                "timestamp": int(time.time() * 1000),
                "status": "closed",
                "symbol": symbol,
                "type": "market",
                "side": "sell",
                "price": current_price,
                "amount": self.position.quantity,
                "filled": self.position.quantity,
                "remaining": 0,
            }
            self.logger.info(f"Order simulated: {order['id']}")
        else:
            # Real execution
            order = self.exchange.create_market_sell_order(symbol, self.position.quantity)
            self.logger.info(f"Order placed: {order['id']}")

        # Calculate realized PNL
        pnl = (current_price - self.position.entry_price) * self.position.quantity
        pnl_pct = (current_price / self.position.entry_price - 1) * 100

        self.logger.info(f"Position closed: PNL = ${pnl:.2f} ({pnl_pct:+.2f}%)")

        # Store trade in database
        self._store_trade(
            symbol=symbol,
            side="sell",
            price=current_price,
            quantity=self.position.quantity,
            signal=signal,
            order_id=order["id"],
            pnl=pnl,
        )

        # Clear position
        self.position = None

        return True

    def _execute_partial_close(
        self, signal: Signal, symbol: str, current_price: float
    ) -> bool:
        """Execute PARTIAL_CLOSE signal (close percentage of position)."""
        if self.position is None:
            self.logger.warning("No position to partially close")
            return False

        close_qty = self.position.quantity * signal.close_percentage
        remaining_qty = self.position.quantity - close_qty

        self.logger.info(
            f"Executing PARTIAL_CLOSE: {close_qty} {symbol} @ {current_price} "
            f"({signal.close_percentage:.1%}, remaining={remaining_qty})"
        )

        # Place market sell order (or simulate in paper mode)
        if self.mode == "paper":
            # Simulated execution
            import time
            order = {
                "id": f"sim_{int(time.time() * 1000)}",
                "timestamp": int(time.time() * 1000),
                "status": "closed",
                "symbol": symbol,
                "type": "market",
                "side": "sell",
                "price": current_price,
                "amount": close_qty,
                "filled": close_qty,
                "remaining": 0,
            }
            self.logger.info(f"Order simulated: {order['id']}")
        else:
            # Real execution
            order = self.exchange.create_market_sell_order(symbol, close_qty)
            self.logger.info(f"Order placed: {order['id']}")

        # Calculate partial PNL
        pnl = (current_price - self.position.entry_price) * close_qty
        pnl_pct = (current_price / self.position.entry_price - 1) * 100

        self.logger.info(f"Partial close: PNL = ${pnl:.2f} ({pnl_pct:+.2f}%)")

        # Store trade in database
        self._store_trade(
            symbol=symbol,
            side="sell",
            price=current_price,
            quantity=close_qty,
            signal=signal,
            order_id=order["id"],
            pnl=pnl,
        )

        # Update position
        self.position.quantity = remaining_qty

        return True

    def update_position_pnl(self, current_price: float):
        """Update unrealized PNL and highest price for current position."""
        if self.position is None:
            return

        # Update unrealized PNL
        self.position.unrealized_pnl = (
            current_price - self.position.entry_price
        ) * self.position.quantity

        # Update highest price (for trailing stops)
        if current_price > self.position.highest_price:
            self.position.highest_price = current_price

    def _store_trade(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: float,
        signal: Signal,
        order_id: str,
        pnl: Optional[float] = None,
    ):
        """Store trade in database."""
        timestamp = int(time.time() * 1000)

        self.db.execute(
            """
            INSERT INTO trades (
                strategy_id, exchange, symbol, timeframe, order_id, side,
                order_type, quantity, price, cost, fee, timestamp, pnl, pnl_percent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self.strategy_id,
                self.exchange_name,
                symbol,
                "1m",  # TODO: Get from strategy config
                order_id,
                side,
                "market",  # Paper mode always uses market orders
                quantity,
                price,
                price * quantity,  # cost
                0.0,  # fee (paper mode has no fees)
                timestamp,
                pnl or 0.0,
                0.0,  # pnl_percent (calculated on close)
            ),
        )

        self.logger.info(f"Trade stored in database: {side} {quantity} @ {price}")

    def get_position_summary(self) -> Dict:
        """Get current position summary."""
        if self.position is None:
            return {"in_position": False}

        pnl_pct = (
            self.position.unrealized_pnl / (self.position.entry_price * self.position.quantity)
        ) * 100

        return {
            "in_position": True,
            "symbol": self.position.symbol,
            "side": self.position.side,
            "entry_price": self.position.entry_price,
            "quantity": self.position.quantity,
            "unrealized_pnl": self.position.unrealized_pnl,
            "pnl_percentage": pnl_pct,
            "highest_price": self.position.highest_price,
            "entry_time": self.position.entry_time,
        }
