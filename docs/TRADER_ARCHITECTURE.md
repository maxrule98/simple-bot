# Trader Architecture Design

## Runtime Modes

We have three runtime modes that should share as much logic as possible:

1. **Live Trading** - Real money, production exchange
2. **Paper Trading** - Simulated orders, production data (sandbox mode)
3. **Backtesting** - Historical replay, no real-time data

## Key Architectural Decisions

### 1. Live vs Paper Trading

**Implementation**: Single `apps/trader/` application with mode flag

```python
# Environment variable controls mode
TRADING_MODE = os.getenv('TRADING_MODE', 'paper')  # live | paper | backtest

# CCXT sandbox mode
if TRADING_MODE == 'paper':
    exchange.set_sandbox_mode(True)
else:
    exchange.set_sandbox_mode(False)
```

**Why unified?**

- Same codebase ensures consistency
- Easier to test (paper first, then live)
- Share WebSocket, strategy, execution logic
- Only execution environment differs

### 2. Code Sharing Between Modes

**Shared Components:**

```
packages/
  websocket/      # Real-time data (trader only)
  execution/      # Order management (all modes)
  strategies/     # Signal generation (all modes)
  indicators/     # Technical analysis (all modes)
  database/       # Data persistence (all modes)

apps/
  trader/         # Live + Paper runtime
  backtester/     # Historical replay runtime
```

**Key Principle**: The strategy logic must be **identical** across all modes.

```python
# Strategy doesn't know what mode it's in
class Strategy:
    def on_candle(self, ohlcv):
        # Same logic for live/paper/backtest
        if self.should_buy():
            self.execute_order('buy', amount)  # Execution layer handles mode
```

## Strategy Plugin Architecture

### Goal: Zero-Hardcoding, Dynamic Loading

**Problem**: We want to:

- Add new strategies without modifying core code
- Configure strategies via YAML
- Run multiple strategies simultaneously
- Hot-reload strategy changes (dev mode)

**Solution**: Strategy as Plugin Pattern

```
config/
  strategies/
    btc_scalper.yaml        # Strategy configuration
    eth_momentum.yaml
    sol_breakout.yaml

packages/
  strategies/
    __init__.py
    base.py                 # BaseStrategy class
    loader.py               # Dynamic strategy loader
    registry.py             # Strategy registry

    conventional/           # Pre-built strategies
      rsi_mean_reversion.py
      macd_crossover.py
      bollinger_breakout.py

    custom/                 # User-defined strategies
      my_strategy.py
```

### Strategy Configuration (YAML)

```yaml
# config/strategies/btc_scalper.yaml

strategy:
  id: "btc-scalper-001"
  name: "BTC 1m Scalper"
  class: "RSIMeanReversion" # Class name in packages/strategies/conventional/

market:
  exchange: "mexc"
  symbol: "BTC/USDT"
  timeframe: "1m"

parameters:
  rsi_period: 14
  rsi_oversold: 30
  rsi_overbought: 70
  position_size_pct: 2.0 # 2% of capital
  stop_loss_pct: 1.0 # 1% stop loss
  take_profit_pct: 2.0 # 2% take profit

indicators:
  - name: "RSI"
    params:
      period: 14
  - name: "SMA"
    params:
      period: 20

risk_management:
  max_position_size: 0.1 # Max 0.1 BTC
  max_daily_trades: 50
  max_daily_loss_pct: 5.0

execution:
  order_type: "limit" # limit | market
  slippage_tolerance: 0.1 # 0.1%

prometheus:
  enabled: true
  push_interval: 1.0 # Push metrics every 1 second
```

### Strategy Base Class

```python
# packages/strategies/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd

class BaseStrategy(ABC):
    """
    Base class that all strategies must inherit from.

    Handles:
    - Configuration loading
    - Indicator management
    - Signal generation interface
    - Position tracking
    - Prometheus metrics
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.strategy_id = config['strategy']['id']
        self.name = config['strategy']['name']
        self.exchange = config['market']['exchange']
        self.symbol = config['market']['symbol']
        self.timeframe = config['market']['timeframe']

        # Runtime state
        self.position = None
        self.capital = 0.0
        self.indicators = {}
        self.history = pd.DataFrame()

    @abstractmethod
    def on_candle(self, candle: Dict[str, float]) -> Optional[str]:
        """
        Called when new candle arrives.

        Args:
            candle: {'timestamp', 'open', 'high', 'low', 'close', 'volume'}

        Returns:
            'buy' | 'sell' | 'close' | None
        """
        pass

    @abstractmethod
    def on_tick(self, price: float) -> Optional[str]:
        """
        Called on every price tick (live/paper only).

        Args:
            price: Current market price

        Returns:
            'buy' | 'sell' | 'close' | None
        """
        pass

    def calculate_position_size(self, price: float) -> float:
        """Calculate position size based on risk parameters."""
        pct = self.config['parameters']['position_size_pct'] / 100
        size = (self.capital * pct) / price

        # Apply max position size limit
        max_size = self.config['risk_management']['max_position_size']
        return min(size, max_size)

    def should_stop_loss(self, current_price: float) -> bool:
        """Check if stop loss triggered."""
        if not self.position:
            return False

        entry_price = self.position['entry_price']
        stop_loss_pct = self.config['parameters']['stop_loss_pct'] / 100

        if self.position['side'] == 'long':
            return current_price < entry_price * (1 - stop_loss_pct)
        else:
            return current_price > entry_price * (1 + stop_loss_pct)

    def should_take_profit(self, current_price: float) -> bool:
        """Check if take profit triggered."""
        if not self.position:
            return False

        entry_price = self.position['entry_price']
        take_profit_pct = self.config['parameters']['take_profit_pct'] / 100

        if self.position['side'] == 'long':
            return current_price > entry_price * (1 + take_profit_pct)
        else:
            return current_price < entry_price * (1 - take_profit_pct)
```

### Example Strategy Implementation

```python
# packages/strategies/conventional/rsi_mean_reversion.py

from packages.strategies.base import BaseStrategy
from packages.indicators.conventional.rsi import calculate_rsi
from typing import Optional

class RSIMeanReversion(BaseStrategy):
    """
    Simple RSI mean reversion strategy.

    Entry:
    - Buy when RSI < oversold threshold
    - Sell when RSI > overbought threshold

    Exit:
    - Stop loss at configured %
    - Take profit at configured %
    """

    def on_candle(self, candle: Dict[str, float]) -> Optional[str]:
        """Process new candle."""
        # Update history
        self.history = self.history.append(candle, ignore_index=True)

        # Calculate RSI
        rsi_period = self.config['parameters']['rsi_period']
        rsi = calculate_rsi(self.history['close'], period=rsi_period)
        current_rsi = rsi.iloc[-1]

        # Store for debugging/metrics
        self.indicators['rsi'] = current_rsi

        # Check exit conditions first
        if self.position:
            current_price = candle['close']

            if self.should_stop_loss(current_price):
                return 'close'

            if self.should_take_profit(current_price):
                return 'close'

        # Check entry conditions
        if not self.position:
            oversold = self.config['parameters']['rsi_oversold']
            overbought = self.config['parameters']['rsi_overbought']

            if current_rsi < oversold:
                return 'buy'
            elif current_rsi > overbought:
                return 'sell'

        return None

    def on_tick(self, price: float) -> Optional[str]:
        """Process price tick - check exit conditions only."""
        if not self.position:
            return None

        if self.should_stop_loss(price):
            return 'close'

        if self.should_take_profit(price):
            return 'close'

        return None
```

### Strategy Loader (Dynamic)

```python
# packages/strategies/loader.py

import importlib
import yaml
from pathlib import Path
from typing import Dict, Any
from packages.strategies.base import BaseStrategy

class StrategyLoader:
    """
    Dynamically load strategies from YAML configuration.
    """

    def __init__(self, config_dir: str = "config/strategies"):
        self.config_dir = Path(config_dir)
        self.strategy_registry = {}

    def load_strategy(self, config_path: str) -> BaseStrategy:
        """
        Load strategy from YAML config.

        Args:
            config_path: Path to strategy YAML file

        Returns:
            Instantiated strategy object
        """
        # Load config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Get strategy class name
        class_name = config['strategy']['class']

        # Dynamically import strategy class
        # Try conventional strategies first
        try:
            module = importlib.import_module(
                f'packages.strategies.conventional.{self._to_snake_case(class_name)}'
            )
            strategy_class = getattr(module, class_name)
        except (ImportError, AttributeError):
            # Try custom strategies
            module = importlib.import_module(
                f'packages.strategies.custom.{self._to_snake_case(class_name)}'
            )
            strategy_class = getattr(module, class_name)

        # Instantiate strategy
        strategy = strategy_class(config)

        return strategy

    def load_all_strategies(self) -> Dict[str, BaseStrategy]:
        """Load all strategies from config directory."""
        strategies = {}

        for yaml_file in self.config_dir.glob("*.yaml"):
            try:
                strategy = self.load_strategy(str(yaml_file))
                strategies[strategy.strategy_id] = strategy
                print(f"✅ Loaded strategy: {strategy.name} ({strategy.strategy_id})")
            except Exception as e:
                print(f"❌ Failed to load {yaml_file.name}: {e}")

        return strategies

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert PascalCase to snake_case."""
        import re
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
```

## Trader Application Structure

```
apps/
  trader/
    __init__.py
    main.py              # Entry point
    runtime.py           # Core trading loop
    config.py            # Configuration management

    modes/
      __init__.py
      live.py            # Live trading mode
      paper.py           # Paper trading mode (thin wrapper)
```

### Main Entry Point

```python
# apps/trader/main.py

import asyncio
import os
from packages.strategies.loader import StrategyLoader
from packages.execution.manager import ExecutionManager
from packages.websocket.websocket import WebSocketManager
from packages.database.db import DatabaseManager
from packages.prometheus.metrics import PrometheusMetrics
from apps.trader.runtime import TradingRuntime

async def main():
    """
    Main entry point for trader application.

    Supports both live and paper trading modes.
    """
    # Load environment
    trading_mode = os.getenv('TRADING_MODE', 'paper')  # live | paper
    strategy_config = os.getenv('STRATEGY_CONFIG', 'btc_scalper.yaml')

    print(f"🚀 Starting trader in {trading_mode.upper()} mode")
    print(f"📋 Strategy config: {strategy_config}")

    # Initialize components
    db = DatabaseManager('data/trading.db')

    # Load strategy
    loader = StrategyLoader()
    strategy = loader.load_strategy(f'config/strategies/{strategy_config}')

    # Setup exchange (with sandbox mode for paper trading)
    exchange_name = strategy.config['market']['exchange']
    execution_manager = ExecutionManager(
        exchange=exchange_name,
        sandbox_mode=(trading_mode == 'paper')
    )

    # Setup WebSocket for real-time data
    websocket = WebSocketManager(
        exchange=exchange_name,
        db_connection=db.connection
    )

    # Setup Prometheus metrics (if enabled)
    prometheus = None
    if strategy.config.get('prometheus', {}).get('enabled'):
        prometheus = PrometheusMetrics(strategy_id=strategy.strategy_id)

    # Create trading runtime
    runtime = TradingRuntime(
        strategy=strategy,
        execution_manager=execution_manager,
        websocket=websocket,
        database=db,
        prometheus=prometheus,
        mode=trading_mode
    )

    # Start trading
    try:
        await runtime.run()
    except KeyboardInterrupt:
        print("\n⏹️  Shutting down gracefully...")
        await runtime.stop()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        await runtime.stop()
        raise

if __name__ == '__main__':
    asyncio.run(main())
```

### Trading Runtime

```python
# apps/trader/runtime.py

import asyncio
from typing import Optional
from packages.strategies.base import BaseStrategy
from packages.execution.manager import ExecutionManager
from packages.websocket.websocket import WebSocketManager
from packages.database.db import DatabaseManager
from packages.prometheus.metrics import PrometheusMetrics

class TradingRuntime:
    """
    Core trading loop that orchestrates:
    - WebSocket data ingestion
    - Strategy signal generation
    - Order execution
    - Position management
    - Metrics publishing
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        execution_manager: ExecutionManager,
        websocket: WebSocketManager,
        database: DatabaseManager,
        prometheus: Optional[PrometheusMetrics],
        mode: str
    ):
        self.strategy = strategy
        self.execution = execution_manager
        self.websocket = websocket
        self.db = database
        self.prometheus = prometheus
        self.mode = mode
        self.running = False

    async def run(self):
        """Start the trading runtime."""
        self.running = True

        # Start WebSocket streams
        await self.websocket.start(
            symbols=[self.strategy.symbol],
            enable_ohlcv=True,
            enable_trades=True,
            enable_orderbook=True,
            enable_ticker=True
        )

        # Subscribe to data streams
        asyncio.create_task(self._process_candles())
        asyncio.create_task(self._process_ticks())
        asyncio.create_task(self._monitor_positions())

        if self.prometheus:
            asyncio.create_task(self._publish_metrics())

        print(f"✅ Trading runtime started: {self.strategy.name}")
        print(f"   Mode: {self.mode.upper()}")
        print(f"   Symbol: {self.strategy.symbol}")
        print(f"   Timeframe: {self.strategy.timeframe}")

        # Keep running
        while self.running:
            await asyncio.sleep(1)

    async def _process_candles(self):
        """Process completed candles through strategy."""
        while self.running:
            # Wait for new candle from WebSocket
            candle = await self.websocket.get_next_candle(
                symbol=self.strategy.symbol,
                timeframe=self.strategy.timeframe
            )

            # Pass to strategy
            signal = self.strategy.on_candle(candle)

            # Execute signal
            if signal:
                await self._execute_signal(signal, candle['close'])

    async def _process_ticks(self):
        """Process live price ticks through strategy."""
        while self.running:
            # Wait for price tick
            tick = await self.websocket.get_next_tick(self.strategy.symbol)

            # Pass to strategy
            signal = self.strategy.on_tick(tick['price'])

            # Execute signal (usually stop loss / take profit)
            if signal:
                await self._execute_signal(signal, tick['price'])

    async def _execute_signal(self, signal: str, price: float):
        """Execute trading signal."""
        try:
            if signal == 'buy':
                size = self.strategy.calculate_position_size(price)
                await self.execution.create_order(
                    symbol=self.strategy.symbol,
                    side='buy',
                    amount=size,
                    price=price,
                    order_type=self.strategy.config['execution']['order_type']
                )

            elif signal == 'sell':
                size = self.strategy.calculate_position_size(price)
                await self.execution.create_order(
                    symbol=self.strategy.symbol,
                    side='sell',
                    amount=size,
                    price=price,
                    order_type=self.strategy.config['execution']['order_type']
                )

            elif signal == 'close':
                await self.execution.close_position(self.strategy.symbol)

        except Exception as e:
            print(f"❌ Execution error: {e}")

    async def _monitor_positions(self):
        """Monitor open positions and sync with strategy state."""
        while self.running:
            # Update strategy position from exchange
            position = await self.execution.get_position(self.strategy.symbol)
            self.strategy.position = position

            await asyncio.sleep(5)  # Check every 5 seconds

    async def _publish_metrics(self):
        """Publish metrics to Prometheus."""
        interval = self.strategy.config['prometheus']['push_interval']

        while self.running:
            # Push strategy state to Prometheus
            self.prometheus.update_strategy_metrics(
                position=self.strategy.position,
                indicators=self.strategy.indicators,
                capital=self.strategy.capital
            )

            await asyncio.sleep(interval)

    async def stop(self):
        """Stop the trading runtime."""
        self.running = False
        await self.websocket.stop()
        print("✅ Trading runtime stopped")
```

## Backtester Differences

The backtester shares the same strategy code but:

1. **No WebSocket** - Reads historical data from database
2. **Fast-forward** - Can replay days in seconds
3. **Simulated execution** - Instant fills, no slippage (configurable)

```python
# apps/backtester/main.py

async def run_backtest(strategy_config: str, start_date: str, end_date: str):
    """
    Run backtest using historical data.

    Key differences from live trader:
    - Data source: Database (not WebSocket)
    - Execution: Simulated fills
    - Speed: Fast-forward replay
    """
    # Load strategy (same loader as trader!)
    loader = StrategyLoader()
    strategy = loader.load_strategy(f'config/strategies/{strategy_config}')

    # Load historical data from database
    candles = db.fetch_ohlcv(
        exchange=strategy.exchange,
        symbol=strategy.symbol,
        timeframe=strategy.timeframe,
        start=start_date,
        end=end_date
    )

    # Replay candles through strategy
    for candle in candles:
        signal = strategy.on_candle(candle)

        if signal:
            # Simulated execution
            execute_simulated_order(signal, candle['close'])

    # Generate backtest report
    generate_report(strategy)
```

## Docker Compose Setup

```yaml
services:
  # Live trading instance - BTC 1m scalper
  trader-btc-live:
    build: .
    command: python -m apps.trader.main
    environment:
      TRADING_MODE: "live"
      STRATEGY_CONFIG: "btc_scalper.yaml"
      MEXC_API_KEY: ${MEXC_API_KEY}
      MEXC_API_SECRET: ${MEXC_API_SECRET}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - prometheus
      - pushgateway

  # Paper trading instance - ETH momentum
  trader-eth-paper:
    build: .
    command: python -m apps.trader.main
    environment:
      TRADING_MODE: "paper"
      STRATEGY_CONFIG: "eth_momentum.yaml"
      MEXC_API_KEY: ${MEXC_SANDBOX_KEY}
      MEXC_API_SECRET: ${MEXC_SANDBOX_SECRET}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
```

## Key Design Principles

### 1. No Hardcoding

- All configuration in YAML files
- Strategies loaded dynamically
- Exchange, symbol, timeframe all configurable

### 2. Modularity

- Strategies are plugins (inherit from BaseStrategy)
- Execution layer abstracted (packages/execution)
- Data layer abstracted (packages/websocket, packages/database)

### 3. Mode Independence

- Strategy doesn't know if it's live/paper/backtest
- Same signal generation logic across all modes
- Mode only affects execution layer

### 4. Horizontal Scaling

- Each Docker container = one strategy instance
- Multiple strategies run in parallel
- Shared database, isolated positions

## Multi-Timeframe Strategy Support

**Requirement**: Strategies must support arbitrary number of timeframes dynamically (no hardcoded HTF/LTF).

### YAML Configuration

```yaml
strategy:
  id: "btc-multi-tf-001"
  name: "BTC Multi-Timeframe Strategy"
  class: "MultiTimeframeStrategy"

market:
  exchange: "mexc"
  symbol: "BTC/USDT"
  primary_timeframe: "1m" # Execution timeframe (fastest)

  # Additional timeframes for analysis (dynamic array)
  timeframes:
    - "1m" # Ultra-short term
    - "5m" # Short term
    - "15m" # Medium term
    - "1h" # Long term
    # Can add any number of timeframes
```

### BaseStrategy Updates

```python
class BaseStrategy(ABC):
    def __init__(self, config: Dict[str, Any]):
        # ...
        self.primary_timeframe = config['market']['primary_timeframe']
        self.timeframes = config['market'].get('timeframes', [self.primary_timeframe])

        # Store candle history per timeframe
        self.history = {
            tf: pd.DataFrame() for tf in self.timeframes
        }

        # Store indicators per timeframe
        self.indicators = {
            tf: {} for tf in self.timeframes
        }

    @abstractmethod
    def on_candle(self, candle: Dict[str, float], timeframe: str) -> Optional[str]:
        """
        Called when new candle arrives for any timeframe.

        Args:
            candle: {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
            timeframe: Which timeframe this candle belongs to (e.g., '1m', '5m')

        Returns:
            'buy' | 'sell' | 'close' | None
        """
        pass
```

### Example Multi-Timeframe Strategy

```python
class MultiTimeframeStrategy(BaseStrategy):
    """
    Trend confirmation across multiple timeframes.

    Logic:
    - All timeframes must agree on trend direction
    - Entry on primary (fastest) timeframe
    - Exit based on any timeframe reversal
    """

    def on_candle(self, candle: Dict[str, float], timeframe: str) -> Optional[str]:
        # Update history for this timeframe
        self.history[timeframe] = self.history[timeframe].append(candle, ignore_index=True)

        # Calculate indicators for this timeframe
        rsi = calculate_rsi(self.history[timeframe]['close'], period=14)
        self.indicators[timeframe]['rsi'] = rsi.iloc[-1]

        # Only generate signals on primary timeframe
        if timeframe != self.primary_timeframe:
            return None

        # Check if all timeframes agree
        all_bullish = all(
            self.indicators[tf]['rsi'] < 30  # Oversold on all timeframes
            for tf in self.timeframes
        )

        all_bearish = all(
            self.indicators[tf]['rsi'] > 70  # Overbought on all timeframes
            for tf in self.timeframes
        )

        if not self.position:
            if all_bullish:
                return 'buy'
            elif all_bearish:
                return 'sell'
        else:
            # Exit if any timeframe reverses
            if self.position['side'] == 'long' and any(
                self.indicators[tf]['rsi'] > 70 for tf in self.timeframes
            ):
                return 'close'
            elif self.position['side'] == 'short' and any(
                self.indicators[tf]['rsi'] < 30 for tf in self.timeframes
            ):
                return 'close'

        return None
```

### Runtime Changes

```python
class TradingRuntime:
    async def _process_candles(self):
        """Process completed candles for ALL configured timeframes."""

        # Subscribe to all timeframes
        for timeframe in self.strategy.timeframes:
            asyncio.create_task(self._process_candle_stream(timeframe))

    async def _process_candle_stream(self, timeframe: str):
        """Process candles for a specific timeframe."""
        while self.running:
            candle = await self.websocket.get_next_candle(
                symbol=self.strategy.symbol,
                timeframe=timeframe
            )

            # Pass timeframe to strategy
            signal = self.strategy.on_candle(candle, timeframe)

            # Only execute on primary timeframe signals
            if signal and timeframe == self.strategy.primary_timeframe:
                await self._execute_signal(signal, candle['close'])
```

### WebSocket Subscription

```python
# WebSocket manager automatically handles multiple timeframes
await self.websocket.start(
    symbols=[self.strategy.symbol],
    timeframes=self.strategy.timeframes,  # Dynamic array
    enable_ohlcv=True,
    enable_trades=True,
    enable_orderbook=True,
    enable_ticker=True
)
```

**Key Design:**

- No hardcoded "HTF" or "LTF" - just an array of timeframes
- Strategy receives candles tagged with timeframe
- Can support 2, 3, 5, or any number of timeframes
- Primary timeframe determines execution frequency
- All other timeframes provide confirmation/context

## Nice-to-Have Features (Future)

### 1. Hot-Reload Strategy Parameters

- Watch YAML config files for changes
- Reload strategy parameters without restart
- Useful for tuning strategies in real-time
- Implementation: File watcher + reload mechanism

### 2. Inter-Strategy Communication

**What is this?** Allow strategies to share information or coordinate.

**Use Cases:**

- Multiple strategies trading same symbol avoid competing orders
- Risk manager broadcasts "stop trading" to all strategies
- Strategies share expensive indicator calculations
- Portfolio-level position limits enforced across strategies

**Example:**

```python
# Strategy A checks if Strategy B is in a position
if message_bus.get_position('strategy-b'):
    # Don't open opposite position
    return None
```

**Status**: Nice to have in future, not needed yet

### 3. Portfolio-Level Risk Management

- Max total exposure across all strategies
- Centralized risk manager service
- Can pause all strategies if portfolio drawdown exceeds limit
- **Status**: Nice to have in future, not needed yet

### 4. Strategy State Persistence (Maybe)

- Persist strategy state between restarts
- Store indicator history in database
- Checkpoint mechanism for quick recovery
- Not critical initially

## Complex Strategies & ML Integration

### The Problem

As strategies become more sophisticated, we need to handle:

1. **Multiple Signal Sources**
   - Technical indicators (RSI, MACD, Bollinger Bands)
   - ML model predictions (LSTM, ARIMA, Random Forest)
   - Order book analysis (liquidity, depth, imbalance)
   - Market microstructure (bid-ask spread, trade flow)
   - Sentiment analysis (social media, news)

2. **Complex Entry Conditions**
   - "Buy when RSI < 30 AND ML model predicts price increase > 2% AND order book shows strong bid support"
   - Multiple conditions with different weights/importance
   - Conditions from different timeframes
   - Ensemble model voting (3 out of 5 models agree)

3. **Complex Exit Logic**
   - Tiered profit-taking: Close 33% at 2%, 33% at 4%, 33% at 6%
   - Trailing stops with dynamic adjustment
   - Time-based exits (close if no profit after 1 hour)
   - ML-based exit predictions
   - Multi-condition exits (technical reversal OR ML prediction OR time limit)

4. **ML Model Management**
   - Model loading and versioning
   - Feature engineering pipelines
   - Inference optimization
   - Model retraining workflows

### Solution: Modular Signal Architecture

Instead of simple string returns ('buy', 'sell', 'close'), use **Signal Objects** with rich metadata.

#### Signal Object Design

```python
from dataclasses import dataclass
from typing import Optional, Dict, List
from enum import Enum

class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"
    HOLD = "hold"
    PARTIAL_CLOSE = "partial_close"

class SignalSource(Enum):
    TECHNICAL = "technical"
    ML_MODEL = "ml_model"
    ORDERBOOK = "orderbook"
    SENTIMENT = "sentiment"
    RISK_MANAGEMENT = "risk_management"

@dataclass
class Signal:
    """
    Rich signal object carrying metadata.
    """
    type: SignalType
    source: SignalSource
    confidence: float  # 0.0 to 1.0

    # Optional metadata
    price: Optional[float] = None
    size_multiplier: float = 1.0  # For partial positions (0.0 to 1.0)
    reason: Optional[str] = None
    metadata: Dict[str, any] = None

    # For partial closes
    close_percentage: Optional[float] = None  # e.g., 0.5 for 50%

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
```

#### Updated BaseStrategy

```python
class BaseStrategy(ABC):
    """
    Enhanced base strategy with signal objects.
    """

    @abstractmethod
    def on_candle(self, candle: Dict[str, float], timeframe: str) -> Optional[List[Signal]]:
        """
        Called when new candle arrives.

        Returns:
            List of Signal objects (can return multiple signals)
            Example: [
                Signal(type=SignalType.PARTIAL_CLOSE, close_percentage=0.5, confidence=0.8),
                Signal(type=SignalType.BUY, confidence=0.9)
            ]
        """
        pass

    @abstractmethod
    def generate_signals(self) -> List[Signal]:
        """
        Generate signals from all available sources.

        Called by on_candle() to aggregate signals.
        """
        pass
```

#### Modular Signal Sources

```python
# Base class for signal sources
class SignalGenerator(ABC):
    """Base class for all signal generators."""

    @abstractmethod
    def generate(self, data: Dict[str, any]) -> List[Signal]:
        """Generate signals from provided data."""
        pass

# Technical indicator signals
class TechnicalSignalGenerator(SignalGenerator):
    def __init__(self, config: Dict[str, any]):
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.rsi_overbought = config.get('rsi_overbought', 70)

    def generate(self, data: Dict[str, any]) -> List[Signal]:
        signals = []
        rsi = data['indicators']['rsi']

        if rsi < self.rsi_oversold:
            signals.append(Signal(
                type=SignalType.BUY,
                source=SignalSource.TECHNICAL,
                confidence=self._calculate_confidence(rsi),
                reason=f"RSI oversold: {rsi:.2f}"
            ))
        elif rsi > self.rsi_overbought:
            signals.append(Signal(
                type=SignalType.SELL,
                source=SignalSource.TECHNICAL,
                confidence=self._calculate_confidence(100 - rsi),
                reason=f"RSI overbought: {rsi:.2f}"
            ))

        return signals

    def _calculate_confidence(self, rsi: float) -> float:
        """Calculate confidence based on how extreme RSI is."""
        if rsi < 30:
            return min(1.0, (30 - rsi) / 30)  # More extreme = higher confidence
        elif rsi > 70:
            return min(1.0, (rsi - 70) / 30)
        return 0.0

# ML model signals
class MLSignalGenerator(SignalGenerator):
    def __init__(self, config: Dict[str, any]):
        self.model_path = config['model_path']
        self.model = self._load_model()
        self.feature_pipeline = self._load_feature_pipeline()

    def generate(self, data: Dict[str, any]) -> List[Signal]:
        # Prepare features
        features = self.feature_pipeline.transform(data['history'])

        # Run inference
        prediction = self.model.predict(features)
        confidence = self.model.predict_proba(features).max()

        signals = []
        if prediction == 1:  # Buy signal
            signals.append(Signal(
                type=SignalType.BUY,
                source=SignalSource.ML_MODEL,
                confidence=confidence,
                reason=f"ML model predicts upward movement (confidence: {confidence:.2f})",
                metadata={'prediction': prediction, 'features': features.tolist()}
            ))
        elif prediction == -1:  # Sell signal
            signals.append(Signal(
                type=SignalType.SELL,
                source=SignalSource.ML_MODEL,
                confidence=confidence,
                reason=f"ML model predicts downward movement (confidence: {confidence:.2f})"
            ))

        return signals

    def _load_model(self):
        """Load trained ML model from disk."""
        import joblib
        return joblib.load(self.model_path)

    def _load_feature_pipeline(self):
        """Load feature engineering pipeline."""
        # Load sklearn pipeline or custom transformer
        pass

# Order book signals
class OrderBookSignalGenerator(SignalGenerator):
    def __init__(self, config: Dict[str, any]):
        self.imbalance_threshold = config.get('imbalance_threshold', 0.6)

    def generate(self, data: Dict[str, any]) -> List[Signal]:
        orderbook = data['orderbook']

        # Calculate bid/ask imbalance
        total_bids = sum(level['quantity'] for level in orderbook['bids'][:10])
        total_asks = sum(level['quantity'] for level in orderbook['asks'][:10])

        if total_bids + total_asks == 0:
            return []

        bid_ratio = total_bids / (total_bids + total_asks)

        signals = []
        if bid_ratio > self.imbalance_threshold:
            signals.append(Signal(
                type=SignalType.BUY,
                source=SignalSource.ORDERBOOK,
                confidence=bid_ratio,
                reason=f"Strong bid support: {bid_ratio:.2%}"
            ))
        elif bid_ratio < (1 - self.imbalance_threshold):
            signals.append(Signal(
                type=SignalType.SELL,
                source=SignalSource.ORDERBOOK,
                confidence=1 - bid_ratio,
                reason=f"Strong ask pressure: {(1-bid_ratio):.2%}"
            ))

        return signals
```

#### Signal Aggregation

```python
class SignalAggregator:
    """
    Combine multiple signals into final decision.

    Strategies:
    - Voting: Majority wins
    - Weighted: Weight by confidence
    - Unanimous: All sources must agree
    - Threshold: Must have X confidence to act
    """

    def __init__(self, mode: str = 'weighted', threshold: float = 0.5):
        self.mode = mode
        self.threshold = threshold

    def aggregate(self, signals: List[Signal]) -> Optional[Signal]:
        """
        Aggregate multiple signals into single decision.
        """
        if not signals:
            return None

        if self.mode == 'voting':
            return self._voting_aggregation(signals)
        elif self.mode == 'weighted':
            return self._weighted_aggregation(signals)
        elif self.mode == 'unanimous':
            return self._unanimous_aggregation(signals)
        else:
            raise ValueError(f"Unknown aggregation mode: {self.mode}")

    def _weighted_aggregation(self, signals: List[Signal]) -> Optional[Signal]:
        """Weight signals by confidence."""
        buy_signals = [s for s in signals if s.type == SignalType.BUY]
        sell_signals = [s for s in signals if s.type == SignalType.SELL]

        buy_weight = sum(s.confidence for s in buy_signals)
        sell_weight = sum(s.confidence for s in sell_signals)

        if buy_weight > sell_weight and buy_weight > self.threshold:
            return Signal(
                type=SignalType.BUY,
                source=SignalSource.TECHNICAL,  # Aggregated
                confidence=buy_weight / len(signals),
                reason=f"Aggregated signal: {len(buy_signals)} buy sources",
                metadata={'sources': [s.source.value for s in buy_signals]}
            )
        elif sell_weight > buy_weight and sell_weight > self.threshold:
            return Signal(
                type=SignalType.SELL,
                source=SignalSource.TECHNICAL,
                confidence=sell_weight / len(signals),
                reason=f"Aggregated signal: {len(sell_signals)} sell sources",
                metadata={'sources': [s.source.value for s in sell_signals]}
            )

        return None

    def _unanimous_aggregation(self, signals: List[Signal]) -> Optional[Signal]:
        """All sources must agree."""
        if not signals:
            return None

        signal_types = set(s.type for s in signals)

        if len(signal_types) == 1:  # All agree
            avg_confidence = sum(s.confidence for s in signals) / len(signals)
            return Signal(
                type=list(signal_types)[0],
                source=SignalSource.TECHNICAL,
                confidence=avg_confidence,
                reason=f"Unanimous agreement from {len(signals)} sources"
            )

        return None
```

#### Complex Strategy Implementation

```python
class ComplexMLStrategy(BaseStrategy):
    """
    Advanced strategy combining technical, ML, and orderbook signals.
    """

    def __init__(self, config: Dict[str, any]):
        super().__init__(config)

        # Initialize signal generators
        self.technical_generator = TechnicalSignalGenerator(config['technical'])
        self.ml_generator = MLSignalGenerator(config['ml'])
        self.orderbook_generator = OrderBookSignalGenerator(config['orderbook'])

        # Initialize signal aggregator
        self.aggregator = SignalAggregator(
            mode=config.get('aggregation_mode', 'weighted'),
            threshold=config.get('signal_threshold', 0.5)
        )

        # Exit manager for complex exits
        self.exit_manager = ExitManager(config['exits'])

    def on_candle(self, candle: Dict[str, float], timeframe: str) -> Optional[List[Signal]]:
        """Generate and aggregate signals."""

        # Only generate entry signals on primary timeframe
        if timeframe != self.primary_timeframe:
            return None

        # Check for exit signals first
        if self.position:
            exit_signals = self.exit_manager.check_exits(
                position=self.position,
                current_price=candle['close'],
                history=self.history[timeframe]
            )
            if exit_signals:
                return exit_signals

        # Generate entry signals
        all_signals = []

        # Technical signals
        tech_signals = self.technical_generator.generate({
            'indicators': self.indicators[timeframe]
        })
        all_signals.extend(tech_signals)

        # ML signals
        ml_signals = self.ml_generator.generate({
            'history': self.history[timeframe]
        })
        all_signals.extend(ml_signals)

        # Order book signals
        if self.orderbook_data:
            ob_signals = self.orderbook_generator.generate({
                'orderbook': self.orderbook_data
            })
            all_signals.extend(ob_signals)

        # Aggregate signals
        final_signal = self.aggregator.aggregate(all_signals)

        return [final_signal] if final_signal else None

class ExitManager:
    """
    Manage complex exit logic.
    """

    def __init__(self, config: Dict[str, any]):
        self.stop_loss_pct = config.get('stop_loss_pct', 1.0)
        self.take_profit_levels = config.get('take_profit_levels', [
            {'target_pct': 2.0, 'close_pct': 0.33},
            {'target_pct': 4.0, 'close_pct': 0.33},
            {'target_pct': 6.0, 'close_pct': 0.34}
        ])
        self.max_hold_time = config.get('max_hold_time_minutes', 60)
        self.trailing_stop_pct = config.get('trailing_stop_pct', 0.5)

    def check_exits(
        self,
        position: Dict[str, any],
        current_price: float,
        history: pd.DataFrame
    ) -> List[Signal]:
        """Check all exit conditions."""
        signals = []

        # Stop loss
        if self._check_stop_loss(position, current_price):
            signals.append(Signal(
                type=SignalType.CLOSE,
                source=SignalSource.RISK_MANAGEMENT,
                confidence=1.0,
                reason="Stop loss triggered"
            ))
            return signals  # Exit immediately

        # Tiered take profit
        tp_signal = self._check_take_profit(position, current_price)
        if tp_signal:
            signals.append(tp_signal)

        # Time-based exit
        time_signal = self._check_time_exit(position, history)
        if time_signal:
            signals.append(time_signal)

        # Trailing stop
        trail_signal = self._check_trailing_stop(position, current_price)
        if trail_signal:
            signals.append(trail_signal)

        return signals

    def _check_stop_loss(self, position: Dict[str, any], price: float) -> bool:
        """Check if stop loss triggered."""
        entry = position['entry_price']
        pnl_pct = ((price - entry) / entry) * 100

        if position['side'] == 'long':
            return pnl_pct < -self.stop_loss_pct
        else:
            return pnl_pct > self.stop_loss_pct

    def _check_take_profit(self, position: Dict[str, any], price: float) -> Optional[Signal]:
        """Check tiered take profit levels."""
        entry = position['entry_price']
        pnl_pct = ((price - entry) / entry) * 100

        for level in self.take_profit_levels:
            if abs(pnl_pct) >= level['target_pct']:
                # Check if this level already hit
                if not position.get(f"tp_{level['target_pct']}_hit"):
                    return Signal(
                        type=SignalType.PARTIAL_CLOSE,
                        source=SignalSource.RISK_MANAGEMENT,
                        confidence=1.0,
                        close_percentage=level['close_pct'],
                        reason=f"Take profit level {level['target_pct']}% reached",
                        metadata={'level': level}
                    )

        return None

    def _check_time_exit(self, position: Dict[str, any], history: pd.DataFrame) -> Optional[Signal]:
        """Exit if held too long without profit."""
        hold_time = (history.iloc[-1]['timestamp'] - position['entry_time']) / 60000  # minutes

        if hold_time > self.max_hold_time:
            return Signal(
                type=SignalType.CLOSE,
                source=SignalSource.RISK_MANAGEMENT,
                confidence=0.7,
                reason=f"Max hold time exceeded: {hold_time:.1f} minutes"
            )

        return None

    def _check_trailing_stop(self, position: Dict[str, any], price: float) -> Optional[Signal]:
        """Trailing stop implementation."""
        # Track highest/lowest price since entry
        if position['side'] == 'long':
            high = position.get('highest_price', position['entry_price'])
            if price > high:
                position['highest_price'] = price
                return None

            # Check if price fell below trailing stop
            drawdown_pct = ((high - price) / high) * 100
            if drawdown_pct > self.trailing_stop_pct:
                return Signal(
                    type=SignalType.CLOSE,
                    source=SignalSource.RISK_MANAGEMENT,
                    confidence=0.9,
                    reason=f"Trailing stop triggered: {drawdown_pct:.2f}% from high"
                )

        return None
```

#### YAML Configuration for Complex Strategy

```yaml
strategy:
  id: "btc-ml-complex-001"
  name: "BTC ML Complex Strategy"
  class: "ComplexMLStrategy"

  # Signal aggregation
  aggregation_mode: "weighted" # voting | weighted | unanimous
  signal_threshold: 0.6

# Technical signals
technical:
  rsi_period: 14
  rsi_oversold: 30
  rsi_overbought: 70

# ML model
ml:
  model_path: "models/btc_lstm_v1.pkl"
  feature_pipeline_path: "models/feature_pipeline.pkl"

# Order book signals
orderbook:
  imbalance_threshold: 0.65

# Complex exits
exits:
  stop_loss_pct: 1.0

  # Tiered take profit
  take_profit_levels:
    - target_pct: 2.0
      close_pct: 0.33 # Close 33% of position
    - target_pct: 4.0
      close_pct: 0.33 # Close another 33%
    - target_pct: 6.0
      close_pct: 0.34 # Close remaining

  max_hold_time_minutes: 60
  trailing_stop_pct: 0.5
```

### Key Benefits

1. **Composability**: Mix and match signal sources
2. **Extensibility**: Add new signal generators without changing core code
3. **ML Integration**: Clean interface for ML models
4. **Complex Exits**: Support any exit logic (partial, tiered, time-based)
5. **Debuggability**: Signals carry metadata showing reasoning
6. **Testing**: Each signal generator can be tested independently

### ML Model Workflow

1. **Training** (offline):

   ```bash
   python scripts/train_model.py --symbol BTC/USDT --model lstm --output models/btc_lstm_v1.pkl
   ```

2. **Feature Pipeline**:

   ```python
   # Saved with model
   feature_pipeline = Pipeline([
       ('scaler', StandardScaler()),
       ('lag_features', LagFeatureTransformer(lags=[1, 5, 10])),
       ('technical', TechnicalFeatureTransformer())
   ])
   ```

3. **Inference** (live):

   ```python
   # MLSignalGenerator handles loading and inference
   signals = ml_generator.generate({'history': candle_history})
   ```

4. **Retraining**:
   - Scheduled job updates model periodically
   - Strategy hot-reloads new model version
   - Versioning tracks model performance

## Complete Working Example

Let me show you exactly how this all fits together with a real execution flow.

### Directory Structure

```
simple-bot/
├── config/
│   └── strategies/
│       └── btc_ml_strategy.yaml       # Strategy config
│
├── models/
│   ├── btc_lstm_v1.pkl                # Trained ML model
│   └── feature_pipeline.pkl           # Feature engineering
│
├── packages/
│   ├── strategies/
│   │   ├── base.py                    # BaseStrategy class
│   │   ├── loader.py                  # Dynamic loader
│   │   └── conventional/
│   │       └── complex_ml_strategy.py # Our strategy
│   │
│   └── signals/                       # NEW: Signal generators
│       ├── __init__.py
│       ├── types.py                   # Signal, SignalType, etc.
│       ├── aggregator.py              # SignalAggregator
│       ├── generators/
│       │   ├── technical.py           # TechnicalSignalGenerator
│       │   ├── ml.py                  # MLSignalGenerator
│       │   └── orderbook.py           # OrderBookSignalGenerator
│       └── exits/
│           └── manager.py             # ExitManager
│
└── apps/
    └── trader/
        ├── main.py                    # Entry point
        └── runtime.py                 # Trading loop
```

### Step 1: Strategy Configuration (YAML)

```yaml
# config/strategies/btc_ml_strategy.yaml

strategy:
  id: "btc-ml-001"
  name: "BTC ML Multi-Signal Strategy"
  class: "ComplexMLStrategy"

  # Signal aggregation settings
  aggregation_mode: "weighted" # Confidence-weighted voting
  signal_threshold: 0.6 # Need 60% confidence to act

market:
  exchange: "mexc"
  symbol: "BTC/USDT"
  primary_timeframe: "1m"

  # Multi-timeframe analysis
  timeframes:
    - "1m" # Entry timeframe
    - "5m" # Confirmation
    - "15m" # Trend context

parameters:
  position_size_pct: 2.0
  max_position_size: 0.1 # 0.1 BTC max

# Technical signal configuration
technical:
  rsi_period: 14
  rsi_oversold: 30
  rsi_overbought: 70

  macd_fast: 12
  macd_slow: 26
  macd_signal: 9

# ML model configuration
ml:
  enabled: true
  model_path: "models/btc_lstm_v1.pkl"
  feature_pipeline_path: "models/feature_pipeline.pkl"
  min_confidence: 0.65 # Only use ML signals with 65%+ confidence

# Order book configuration
orderbook:
  enabled: true
  imbalance_threshold: 0.65 # 65% bid or ask dominance
  depth_levels: 10 # Analyze top 10 levels

# Complex exit management
exits:
  stop_loss_pct: 1.0 # 1% stop loss

  # Tiered take profit
  take_profit_levels:
    - target_pct: 2.0
      close_pct: 0.33 # Close 33% at 2% profit
    - target_pct: 4.0
      close_pct: 0.33 # Close 33% at 4% profit
    - target_pct: 6.0
      close_pct: 0.34 # Close remaining at 6% profit

  max_hold_time_minutes: 60 # Exit after 1 hour
  trailing_stop_pct: 0.5 # 0.5% trailing stop

risk_management:
  max_daily_trades: 50
  max_daily_loss_pct: 5.0

execution:
  order_type: "limit"
  slippage_tolerance: 0.1

prometheus:
  enabled: true
  push_interval: 1.0
```

### Step 2: Execution Flow

#### Timestamp: 10:30:00 - New 1m Candle Arrives

```python
# apps/trader/runtime.py processes new candle

# 1. WebSocket receives candle
candle = {
    'timestamp': 1735293000000,
    'open': 42150.50,
    'high': 42180.25,
    'low': 42145.00,
    'close': 42165.75,
    'volume': 125.50,
    'timeframe': '1m'
}

# 2. Runtime passes to strategy
signals = strategy.on_candle(candle, timeframe='1m')
```

#### Inside ComplexMLStrategy.on_candle()

```python
def on_candle(self, candle: Dict, timeframe: str) -> Optional[List[Signal]]:
    """
    Process candle and generate signals.
    """

    # Update history for this timeframe
    self.history[timeframe] = self.history[timeframe].append(candle, ignore_index=True)

    # Calculate indicators for this timeframe
    self._update_indicators(timeframe)

    # Only generate signals on primary timeframe (1m)
    if timeframe != self.primary_timeframe:
        return None

    # Check exits first (if in position)
    if self.position:
        exit_signals = self.exit_manager.check_exits(
            position=self.position,
            current_price=candle['close'],
            history=self.history[timeframe]
        )
        if exit_signals:
            self._log_signals(exit_signals, candle)
            return exit_signals

    # Generate entry signals from all sources
    all_signals = self.generate_signals()

    # Aggregate signals
    final_signal = self.aggregator.aggregate(all_signals)

    if final_signal:
        self._log_signals([final_signal], candle)
        return [final_signal]

    return None

def generate_signals(self) -> List[Signal]:
    """Collect signals from all sources."""
    all_signals = []

    # 1. Technical indicators
    tech_signals = self.technical_generator.generate({
        'indicators': self.indicators[self.primary_timeframe],
        'history': self.history[self.primary_timeframe]
    })
    all_signals.extend(tech_signals)

    # 2. ML model predictions
    if self.config['ml']['enabled']:
        ml_signals = self.ml_generator.generate({
            'history': self.history[self.primary_timeframe]
        })
        all_signals.extend(ml_signals)

    # 3. Order book analysis
    if self.config['orderbook']['enabled'] and self.orderbook_data:
        ob_signals = self.orderbook_generator.generate({
            'orderbook': self.orderbook_data
        })
        all_signals.extend(ob_signals)

    return all_signals
```

#### Signal Generation Breakdown

```python
# Technical Signal Generator Output
tech_signal = Signal(
    type=SignalType.BUY,
    source=SignalSource.TECHNICAL,
    confidence=0.75,
    reason="RSI oversold (28.5) + MACD bullish crossover",
    metadata={
        'rsi': 28.5,
        'macd': 0.015,
        'macd_signal': -0.005,
        'timeframes_agree': ['1m', '5m']  # Both showing oversold
    }
)

# ML Model Generator Output
ml_signal = Signal(
    type=SignalType.BUY,
    source=SignalSource.ML_MODEL,
    confidence=0.82,
    reason="LSTM predicts 2.5% upward movement (82% confidence)",
    metadata={
        'prediction': 0.025,  # 2.5% up
        'model_version': 'btc_lstm_v1',
        'features': {
            'price_momentum_1m': 0.015,
            'volume_ratio': 1.35,
            'volatility': 0.008
        }
    }
)

# Order Book Generator Output
ob_signal = Signal(
    type=SignalType.BUY,
    source=SignalSource.ORDERBOOK,
    confidence=0.68,
    reason="Strong bid support: 68% bid dominance",
    metadata={
        'bid_ratio': 0.68,
        'total_bids': 145.5,  # BTC
        'total_asks': 68.2,   # BTC
        'spread': 0.50        # $0.50
    }
)
```

#### Signal Aggregation

```python
# SignalAggregator.aggregate() with mode='weighted'

all_signals = [tech_signal, ml_signal, ob_signal]

# All are BUY signals, calculate weighted confidence
buy_weight = 0.75 + 0.82 + 0.68 = 2.25
avg_confidence = 2.25 / 3 = 0.75

# Threshold check: 0.75 > 0.6 ✓
# Generate aggregated signal

final_signal = Signal(
    type=SignalType.BUY,
    source=SignalSource.TECHNICAL,  # Marked as aggregated
    confidence=0.75,
    reason="Aggregated signal: 3 buy sources (technical, ml_model, orderbook)",
    metadata={
        'sources': ['technical', 'ml_model', 'orderbook'],
        'individual_confidences': [0.75, 0.82, 0.68],
        'aggregation_mode': 'weighted'
    }
)
```

### Step 3: Order Execution

```python
# apps/trader/runtime.py executes signal

await self._execute_signal(final_signal, candle['close'])

async def _execute_signal(self, signal: Signal, price: float):
    """Execute trading signal."""

    if signal.type == SignalType.BUY:
        # Calculate position size
        size = self.strategy.calculate_position_size(price)

        # Log execution intent
        self.logger.info(
            f"🟢 EXECUTING BUY SIGNAL",
            extra={
                'signal': signal.to_dict(),
                'price': price,
                'size': size,
                'value': price * size
            }
        )

        # Place order via execution manager
        order = await self.execution.create_order(
            symbol=self.strategy.symbol,
            side='buy',
            amount=size,
            price=price,
            order_type=self.strategy.config['execution']['order_type']
        )

        # Update position
        self.strategy.position = {
            'side': 'long',
            'entry_price': order['executed_price'],
            'entry_time': order['timestamp'],
            'size': order['filled'],
            'order_id': order['id']
        }

        # Push metrics to Prometheus
        if self.prometheus:
            self.prometheus.record_trade(
                side='buy',
                price=order['executed_price'],
                size=order['filled'],
                signal_confidence=signal.confidence
            )
```

### Step 4: Console Output

```
🚀 Starting trader in PAPER mode
📋 Strategy config: btc_ml_strategy.yaml

✅ Loaded strategy: BTC ML Multi-Signal Strategy (btc-ml-001)
   Exchange: mexc (sandbox)
   Symbol: BTC/USDT
   Primary Timeframe: 1m
   Additional Timeframes: 5m, 15m

🔌 Connecting to WebSocket...
✅ WebSocket connected: mexc
   Subscribed to: BTC/USDT [1m, 5m, 15m]
   Streams: OHLCV, Trades, OrderBook, Ticker

🤖 Loading ML model: models/btc_lstm_v1.pkl
✅ ML model loaded: LSTM (v1.0.3)

📊 Strategy active - waiting for signals...

[10:30:00] 📈 New 1m candle: BTC/USDT
           O: $42,150.50  H: $42,180.25  L: $42,145.00  C: $42,165.75  V: 125.50

[10:30:01] 🔍 Signal Generation:

           📊 Technical Signal:
              Type: BUY
              Confidence: 75%
              Reason: RSI oversold (28.5) + MACD bullish crossover

           🤖 ML Model Signal:
              Type: BUY
              Confidence: 82%
              Reason: LSTM predicts 2.5% upward movement

           📖 Order Book Signal:
              Type: BUY
              Confidence: 68%
              Reason: Strong bid support (68% dominance)

[10:30:01] ✅ AGGREGATED SIGNAL: BUY (75% confidence)
           Sources: technical, ml_model, orderbook
           Threshold: 0.6 ✓

[10:30:02] 🟢 EXECUTING BUY SIGNAL
           Price: $42,165.75
           Size: 0.0475 BTC
           Value: $2,002.87
           Order Type: limit

[10:30:03] ✅ Order Filled: #mexc_1234567890
           Side: BUY
           Price: $42,165.75
           Size: 0.0475 BTC
           Fee: $0.20 USDT

[10:30:03] 📊 Position Opened:
           Side: LONG
           Entry: $42,165.75
           Size: 0.0475 BTC
           Value: $2,002.87

           Exit Targets:
           ├─ 33% @ $42,993.47 (+2.0%)
           ├─ 33% @ $43,821.18 (+4.0%)
           └─ 34% @ $44,648.90 (+6.0%)

           Stop Loss: $41,744.09 (-1.0%)
           Max Hold: 60 minutes
           Trailing Stop: 0.5%

[10:45:00] 📈 New 1m candle: BTC/USDT
           O: $42,690.00  H: $42,730.50  L: $42,680.25  C: $42,715.80

[10:45:01] 💰 Unrealized PNL: +$26.15 (+1.30%)
           Highest Price: $42,730.50
           Trailing Stop: $42,516.90

[10:50:00] 📈 New 1m candle: BTC/USDT
           O: $42,950.25  H: $43,010.00  L: $42,945.50  C: $42,995.75

[10:50:01] 🎯 Take Profit Level 1 Reached!
           Target: +2.0% ✓
           Close: 33% of position (0.0157 BTC)

[10:50:02] 🟡 EXECUTING PARTIAL CLOSE
           Close: 33%
           Size: 0.0157 BTC
           Price: $42,995.75
           Reason: Take profit level 2.0% reached

[10:50:03] ✅ Order Filled: #mexc_1234567891
           Side: SELL
           Price: $42,995.75
           Size: 0.0157 BTC

[10:50:03] 💰 Realized PNL: +$13.02 (+2.0%)

[10:50:03] 📊 Position Updated:
           Side: LONG
           Remaining: 0.0318 BTC (67%)
           Entry: $42,165.75
           Current: $42,995.75
           Unrealized PNL: +$26.40 (+2.0%)

[11:05:00] 📈 New 1m candle: BTC/USDT
           O: $43,780.50  H: $43,845.00  L: $43,765.25  C: $43,820.75

[11:05:01] 🎯 Take Profit Level 2 Reached!
           Target: +4.0% ✓
           Close: 33% of original position (0.0157 BTC)

[11:05:02] 🟡 EXECUTING PARTIAL CLOSE
           Close: 49% of remaining
           Size: 0.0157 BTC
           Price: $43,820.75

[11:05:03] ✅ Order Filled: #mexc_1234567892

[11:05:03] 💰 Realized PNL: +$25.99 (+4.0%)
           Total Realized: +$39.01

[11:05:03] 📊 Position Updated:
           Side: LONG
           Remaining: 0.0161 BTC (34%)
           Unrealized PNL: +$26.65 (+4.0%)

[11:20:00] 📈 New 1m candle: BTC/USDT
           O: $44,620.00  H: $44,680.25  L: $44,595.50  C: $44,650.80

[11:20:01] 🎯 Take Profit Level 3 Reached!
           Target: +6.0% ✓
           Close: Remaining position (0.0161 BTC)

[11:20:02] 🔴 EXECUTING FULL CLOSE
           Size: 0.0161 BTC
           Price: $44,650.80
           Reason: Take profit level 6.0% reached

[11:20:03] ✅ Order Filled: #mexc_1234567893

[11:20:03] 💰 Final Realized PNL: +$40.01 (+6.0%)
           Total Trade PNL: +$79.02 (+3.95%)

           Entry: $42,165.75
           Exit: Tiered (2%, 4%, 6%)
           Duration: 50 minutes
           ROI: 3.95%

[11:20:03] ✅ Position Closed

           Trade Summary:
           ├─ Entry: $42,165.75 (0.0475 BTC)
           ├─ Exit 1: $42,995.75 (0.0157 BTC) @ +2.0%
           ├─ Exit 2: $43,820.75 (0.0157 BTC) @ +4.0%
           └─ Exit 3: $44,650.80 (0.0161 BTC) @ +6.0%

           Total PNL: +$79.02 (+3.95%)
           Fees: -$0.60
           Net: +$78.42

           Signal Quality:
           └─ All 3 sources agreed (technical, ml, orderbook)

📊 Strategy active - waiting for signals...
```

### Step 5: Database State

```sql
-- trades table
INSERT INTO trades (
    strategy_id, exchange, symbol, side,
    entry_price, exit_price, quantity,
    pnl, pnl_percentage, entry_time, exit_time
) VALUES (
    'btc-ml-001', 'mexc', 'BTC/USDT', 'long',
    42165.75, 44650.80, 0.0475,
    79.02, 3.95, 1735293000000, 1735296003000
);

-- signals table
INSERT INTO signals (
    strategy_id, exchange, symbol, timeframe,
    signal_type, confidence, metadata, timestamp
) VALUES (
    'btc-ml-001', 'mexc', 'BTC/USDT', '1m',
    'buy', 0.75, '{"sources": ["technical", "ml_model", "orderbook"], ...}',
    1735293001000
);
```

### Step 6: Prometheus Metrics

```
# Live metrics pushed to Prometheus

crypto_price{exchange="mexc", symbol="BTC/USDT"} 44650.80

crypto_position_size{strategy_id="btc-ml-001"} 0.0

crypto_position_pnl{strategy_id="btc-ml-001"} 79.02

crypto_trade_count{strategy_id="btc-ml-001"} 1

crypto_signal_confidence{strategy_id="btc-ml-001", type="buy"} 0.75

crypto_ml_prediction{strategy_id="btc-ml-001"} 0.025
```

### Summary

This example shows:

1. ✅ **YAML Configuration** - All strategy settings in one file
2. ✅ **Multi-Source Signals** - Technical + ML + OrderBook
3. ✅ **Signal Aggregation** - Weighted voting with confidence threshold
4. ✅ **Complex Exits** - Tiered take-profit (33% @ 2%, 33% @ 4%, 34% @ 6%)
5. ✅ **Rich Logging** - Every decision is explained
6. ✅ **Database Persistence** - All trades and signals recorded
7. ✅ **Prometheus Metrics** - Live dashboard updates
8. ✅ **Modular Design** - Each component is independent and testable

The key insight: **The strategy doesn't hardcode any logic**. All decision-making is driven by pluggable signal generators configured via YAML. Want to add sentiment analysis? Just add another signal generator. Want to change exit logic? Update the YAML config.

## ML Model Training Pipeline

### Overview

We train models on **rolling windows** of data combining historical + live data from our database. This ensures models adapt to changing market conditions.

### Training Architecture

```
Data Sources → Feature Engineering → Model Training → Evaluation → Deployment
     ↓                  ↓                   ↓              ↓            ↓
  Database      Transform Pipeline    Fit Model     Backtest    Hot-swap
```

### Directory Structure

```
simple-bot/
├── scripts/
│   └── train_model.py           # Training script
│
├── packages/
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── data_loader.py       # Load data from database
│   │   ├── feature_engineering.py
│   │   ├── models/
│   │   │   ├── lstm.py
│   │   │   ├── random_forest.py
│   │   │   └── xgboost.py
│   │   ├── evaluation.py        # Model evaluation
│   │   └── deployment.py        # Model versioning & deployment
│   │
│   └── indicators/
│       └── conventional/        # Technical indicators used as features
│
├── models/
│   ├── btc_lstm_v1.pkl          # Production model
│   ├── btc_lstm_v2.pkl          # New candidate model
│   ├── feature_pipeline.pkl     # Feature transformer
│   └── metadata/
│       └── btc_lstm_v1.json     # Model metadata
│
└── config/
    └── ml/
        └── btc_lstm_config.yaml # Training configuration
```

### Training Configuration (YAML)

```yaml
# config/ml/btc_lstm_config.yaml

training:
  model_name: "btc_lstm"
  model_type: "lstm" # lstm | random_forest | xgboost
  version: "v2"

data:
  exchange: "mexc"
  symbol: "BTC/USDT"
  timeframe: "1m"

  # Rolling window configuration
  window_size_days: 30 # Train on last 30 days
  validation_split: 0.2 # 20% for validation

  # Continuous learning
  rolling_update: true # Use rolling window
  update_frequency: "daily" # Retrain daily
  min_new_data_hours: 24 # Need 24 hours of new data to retrain

features:
  # Price-based features
  price_features:
    - close
    - high
    - low
    - open
    - volume

  # Technical indicators (calculated automatically)
  technical_indicators:
    - name: "RSI"
      params:
        period: 14
    - name: "MACD"
      params:
        fast: 12
        slow: 26
        signal: 9
    - name: "BB"
      params:
        period: 20
        std_dev: 2
    - name: "SMA"
      params:
        periods: [10, 20, 50, 200]
    - name: "EMA"
      params:
        periods: [12, 26]

  # Lag features (previous values)
  lag_features:
    periods: [1, 2, 3, 5, 10, 20, 30, 60] # 1m, 2m, 3m, 5m, 10m, 20m, 30m, 1h

  # Time-based features
  time_features:
    - hour_of_day
    - day_of_week
    - is_trading_hours # US market hours

  # Order book features (if available)
  orderbook_features:
    - bid_ask_spread
    - orderbook_imbalance
    - top_level_liquidity

target:
  # What are we predicting?
  type: "price_direction" # price_direction | price_change | volatility

  # For price_direction
  lookahead_periods: 5 # Predict direction 5 candles ahead (5 minutes)
  threshold_pct: 0.5 # >0.5% = up, <-0.5% = down, else = neutral

  # For price_change
  # predict_returns: true
  # lookahead_periods: 5

model:
  # LSTM configuration
  lstm:
    layers: [128, 64, 32]
    dropout: 0.2
    activation: "relu"
    optimizer: "adam"
    learning_rate: 0.001
    batch_size: 64
    epochs: 100
    early_stopping_patience: 10

  # Random Forest configuration
  random_forest:
    n_estimators: 200
    max_depth: 20
    min_samples_split: 10
    min_samples_leaf: 5

  # XGBoost configuration
  xgboost:
    n_estimators: 200
    max_depth: 10
    learning_rate: 0.1
    subsample: 0.8

evaluation:
  # Metrics to track
  metrics:
    - accuracy
    - precision
    - recall
    - f1_score
    - confusion_matrix
    - profit_factor # If we traded on predictions

  # Backtest evaluation
  backtest:
    enabled: true
    start_date: "2026-01-01"
    end_date: "2026-01-27"
    initial_capital: 10000
    position_size_pct: 2.0

deployment:
  # When to deploy new model
  min_accuracy_improvement: 0.02 # Need 2% better accuracy
  min_profit_factor: 1.5 # Must be profitable in backtest

  # Hot-swap settings
  auto_deploy: false # Manual approval
  rollback_on_performance_drop: true
```

### Training Script

```python
# scripts/train_model.py

import argparse
import yaml
from datetime import datetime, timedelta
from packages.ml.data_loader import DataLoader
from packages.ml.feature_engineering import FeatureEngineer
from packages.ml.models.lstm import LSTMModel
from packages.ml.evaluation import ModelEvaluator
from packages.ml.deployment import ModelDeployer
from packages.database.db import DatabaseManager

def main():
    parser = argparse.ArgumentParser(description='Train ML model')
    parser.add_argument('--config', required=True, help='Path to training config YAML')
    parser.add_argument('--mode', default='train', choices=['train', 'evaluate', 'deploy'])
    args = parser.parse_args()

    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    print(f"🤖 Starting ML Training Pipeline")
    print(f"   Model: {config['training']['model_name']}")
    print(f"   Version: {config['training']['version']}")
    print(f"   Symbol: {config['data']['symbol']}")

    # Initialize components
    db = DatabaseManager('data/trading.db')
    data_loader = DataLoader(db, config)
    feature_engineer = FeatureEngineer(config)

    # 1. Load data from database
    print(f"\n📊 Loading data...")
    df = data_loader.load_training_data()
    print(f"   Loaded {len(df)} candles")
    print(f"   Date range: {df.index[0]} to {df.index[-1]}")

    # 2. Engineer features
    print(f"\n⚙️  Engineering features...")
    X, y = feature_engineer.transform(df)
    print(f"   Features: {X.shape[1]} columns")
    print(f"   Samples: {X.shape[0]} rows")

    # 3. Train model
    if args.mode == 'train':
        print(f"\n🏋️  Training model...")
        model = LSTMModel(config)
        history = model.fit(X, y)

        print(f"   Training complete!")
        print(f"   Final accuracy: {history['accuracy'][-1]:.4f}")
        print(f"   Final loss: {history['loss'][-1]:.4f}")

        # Save model
        model.save(f"models/{config['training']['model_name']}_{config['training']['version']}.pkl")
        feature_engineer.save_pipeline(f"models/feature_pipeline.pkl")
        print(f"\n💾 Model saved")

    # 4. Evaluate model
    if args.mode in ['train', 'evaluate']:
        print(f"\n📈 Evaluating model...")
        evaluator = ModelEvaluator(config)

        # Load model if only evaluating
        if args.mode == 'evaluate':
            model = LSTMModel.load(f"models/{config['training']['model_name']}_{config['training']['version']}.pkl")

        # Validation metrics
        metrics = evaluator.evaluate(model, X, y)
        print(f"\n   Metrics:")
        print(f"   ├─ Accuracy:  {metrics['accuracy']:.4f}")
        print(f"   ├─ Precision: {metrics['precision']:.4f}")
        print(f"   ├─ Recall:    {metrics['recall']:.4f}")
        print(f"   └─ F1 Score:  {metrics['f1_score']:.4f}")

        # Backtest evaluation
        if config['evaluation']['backtest']['enabled']:
            print(f"\n🔄 Running backtest...")
            backtest_results = evaluator.backtest(model, feature_engineer)

            print(f"\n   Backtest Results:")
            print(f"   ├─ Total Trades:   {backtest_results['total_trades']}")
            print(f"   ├─ Winning Trades: {backtest_results['winning_trades']}")
            print(f"   ├─ Win Rate:       {backtest_results['win_rate']:.2%}")
            print(f"   ├─ Profit Factor:  {backtest_results['profit_factor']:.2f}")
            print(f"   ├─ Total PNL:      ${backtest_results['total_pnl']:.2f}")
            print(f"   └─ ROI:            {backtest_results['roi']:.2%}")

    # 5. Deploy model
    if args.mode == 'deploy':
        print(f"\n🚀 Deploying model...")
        deployer = ModelDeployer(config)

        # Check if model meets deployment criteria
        if deployer.should_deploy(metrics, backtest_results):
            deployer.deploy(
                model_path=f"models/{config['training']['model_name']}_{config['training']['version']}.pkl",
                feature_pipeline_path="models/feature_pipeline.pkl"
            )
            print(f"   ✅ Model deployed to production")
        else:
            print(f"   ❌ Model does not meet deployment criteria")

if __name__ == '__main__':
    main()
```

### Data Loader (Rolling Window)

```python
# packages/ml/data_loader.py

from datetime import datetime, timedelta
import pandas as pd
from packages.database.db import DatabaseManager

class DataLoader:
    """
    Load training data from database with rolling window support.
    """

    def __init__(self, db: DatabaseManager, config: dict):
        self.db = db
        self.config = config

    def load_training_data(self) -> pd.DataFrame:
        """
        Load data using rolling window approach.

        Returns:
            DataFrame with OHLCV data
        """
        # Calculate date range
        end_date = datetime.now()
        window_days = self.config['data']['window_size_days']
        start_date = end_date - timedelta(days=window_days)

        # Load OHLCV data from database
        query = """
        SELECT timestamp, open, high, low, close, volume
        FROM ohlcv_data
        WHERE exchange = ?
          AND symbol = ?
          AND timeframe = ?
          AND timestamp >= ?
          AND timestamp <= ?
        ORDER BY timestamp ASC
        """

        df = pd.read_sql(
            query,
            self.db.connection,
            params=[
                self.config['data']['exchange'],
                self.config['data']['symbol'],
                self.config['data']['timeframe'],
                int(start_date.timestamp() * 1000),
                int(end_date.timestamp() * 1000)
            ]
        )

        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        return df

    def load_incremental_data(self, last_timestamp: int) -> pd.DataFrame:
        """
        Load only new data since last training.

        Used for continuous learning.
        """
        query = """
        SELECT timestamp, open, high, low, close, volume
        FROM ohlcv_data
        WHERE exchange = ?
          AND symbol = ?
          AND timeframe = ?
          AND timestamp > ?
        ORDER BY timestamp ASC
        """

        df = pd.read_sql(
            query,
            self.db.connection,
            params=[
                self.config['data']['exchange'],
                self.config['data']['symbol'],
                self.config['data']['timeframe'],
                last_timestamp
            ]
        )

        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        return df
```

### Feature Engineering

```python
# packages/ml/feature_engineering.py

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from packages.indicators.conventional.rsi import calculate_rsi
from packages.indicators.conventional.macd import calculate_macd
from packages.indicators.conventional.bollinger_bands import calculate_bb

class FeatureEngineer:
    """
    Transform raw OHLCV data into ML features.
    """

    def __init__(self, config: dict):
        self.config = config
        self.pipeline = None
        self.feature_columns = []

    def transform(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        """
        Transform raw data into features and target.

        Returns:
            X: Feature DataFrame
            y: Target Series
        """
        df = df.copy()

        # 1. Calculate technical indicators
        df = self._add_technical_indicators(df)

        # 2. Add lag features
        df = self._add_lag_features(df)

        # 3. Add time features
        df = self._add_time_features(df)

        # 4. Calculate target variable
        df = self._calculate_target(df)

        # 5. Drop NaN rows (from indicators & lags)
        df.dropna(inplace=True)

        # 6. Split features and target
        y = df['target']
        X = df.drop(columns=['target', 'open', 'high', 'low', 'close', 'volume'])

        # 7. Store feature columns
        self.feature_columns = X.columns.tolist()

        # 8. Scale features
        if self.pipeline is None:
            self.pipeline = Pipeline([
                ('scaler', StandardScaler())
            ])
            X_scaled = self.pipeline.fit_transform(X)
        else:
            X_scaled = self.pipeline.transform(X)

        X_scaled = pd.DataFrame(X_scaled, columns=X.columns, index=X.index)

        return X_scaled, y

    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators as features."""
        for indicator in self.config['features']['technical_indicators']:
            name = indicator['name']
            params = indicator.get('params', {})

            if name == 'RSI':
                df['rsi'] = calculate_rsi(df['close'], period=params.get('period', 14))

            elif name == 'MACD':
                macd, signal, hist = calculate_macd(
                    df['close'],
                    fast=params.get('fast', 12),
                    slow=params.get('slow', 26),
                    signal=params.get('signal', 9)
                )
                df['macd'] = macd
                df['macd_signal'] = signal
                df['macd_hist'] = hist

            elif name == 'BB':
                upper, middle, lower = calculate_bb(
                    df['close'],
                    period=params.get('period', 20),
                    std_dev=params.get('std_dev', 2)
                )
                df['bb_upper'] = upper
                df['bb_middle'] = middle
                df['bb_lower'] = lower
                df['bb_width'] = (upper - lower) / middle

            elif name == 'SMA':
                for period in params.get('periods', [20]):
                    df[f'sma_{period}'] = df['close'].rolling(period).mean()

            elif name == 'EMA':
                for period in params.get('periods', [12]):
                    df[f'ema_{period}'] = df['close'].ewm(span=period).mean()

        return df

    def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add lagged price features."""
        periods = self.config['features']['lag_features']['periods']

        for period in periods:
            df[f'close_lag_{period}'] = df['close'].shift(period)
            df[f'volume_lag_{period}'] = df['volume'].shift(period)
            df[f'return_lag_{period}'] = df['close'].pct_change(period)

        return df

    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add time-based features."""
        df['hour'] = df.index.hour
        df['day_of_week'] = df.index.dayofweek
        df['is_trading_hours'] = df['hour'].between(9, 16).astype(int)

        return df

    def _calculate_target(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate target variable."""
        target_config = self.config['target']
        lookahead = target_config['lookahead_periods']

        if target_config['type'] == 'price_direction':
            # Calculate future return
            df['future_return'] = df['close'].pct_change(lookahead).shift(-lookahead)

            # Classify as up (1), down (-1), or neutral (0)
            threshold = target_config['threshold_pct'] / 100
            df['target'] = 0
            df.loc[df['future_return'] > threshold, 'target'] = 1   # Up
            df.loc[df['future_return'] < -threshold, 'target'] = -1  # Down

        elif target_config['type'] == 'price_change':
            # Predict exact return
            df['target'] = df['close'].pct_change(lookahead).shift(-lookahead)

        return df

    def save_pipeline(self, path: str):
        """Save feature pipeline for deployment."""
        import joblib
        joblib.dump({
            'pipeline': self.pipeline,
            'feature_columns': self.feature_columns,
            'config': self.config
        }, path)

    @staticmethod
    def load_pipeline(path: str):
        """Load saved feature pipeline."""
        import joblib
        return joblib.load(path)
```

### Continuous Learning (Rolling Window)

```python
# scripts/continuous_training.py

import schedule
import time
from datetime import datetime, timedelta
from packages.ml.data_loader import DataLoader
from packages.ml.feature_engineering import FeatureEngineer
from packages.ml.models.lstm import LSTMModel
from packages.ml.deployment import ModelDeployer

class ContinuousTrainer:
    """
    Continuously retrain model on rolling window of data.
    """

    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.last_training_time = None
        self.current_model_version = None

    def should_retrain(self) -> bool:
        """Check if we have enough new data to retrain."""
        if self.last_training_time is None:
            return True

        # Check if enough time has passed
        min_hours = self.config['data']['min_new_data_hours']
        time_since_last = datetime.now() - self.last_training_time

        return time_since_last.total_seconds() > (min_hours * 3600)

    def retrain(self):
        """Retrain model on latest data."""
        print(f"\n🔄 [{datetime.now()}] Starting continuous training...")

        # Load latest data (rolling window)
        data_loader = DataLoader(db, self.config)
        df = data_loader.load_training_data()

        print(f"   Data: {len(df)} candles ({df.index[0]} to {df.index[-1]})")

        # Engineer features
        feature_engineer = FeatureEngineer(self.config)
        X, y = feature_engineer.transform(df)

        # Train model
        model = LSTMModel(self.config)
        model.fit(X, y)

        # Evaluate
        metrics = model.evaluate(X, y)

        # Save new version
        new_version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        model_path = f"models/{self.config['training']['model_name']}_{new_version}.pkl"
        model.save(model_path)

        print(f"   ✅ New model trained: {new_version}")
        print(f"   Accuracy: {metrics['accuracy']:.4f}")

        # Deploy if better than current
        deployer = ModelDeployer(self.config)
        if deployer.is_better_than_production(metrics):
            deployer.deploy(model_path, "models/feature_pipeline.pkl")
            print(f"   🚀 Deployed to production")
        else:
            print(f"   ⏸️  Not deployed (performance not better)")

        self.last_training_time = datetime.now()

    def run(self):
        """Start continuous training loop."""
        frequency = self.config['data']['update_frequency']

        if frequency == 'hourly':
            schedule.every().hour.do(self.check_and_retrain)
        elif frequency == 'daily':
            schedule.every().day.at("02:00").do(self.check_and_retrain)
        elif frequency == 'weekly':
            schedule.every().sunday.at("02:00").do(self.check_and_retrain)

        print(f"🔄 Continuous training started ({frequency})")

        while True:
            schedule.run_pending()
            time.sleep(60)

    def check_and_retrain(self):
        """Check if retraining needed and execute."""
        if self.should_retrain():
            self.retrain()

# Run continuous training
if __name__ == '__main__':
    trainer = ContinuousTrainer('config/ml/btc_lstm_config.yaml')
    trainer.run()
```

### Docker Compose for Training

```yaml
# docker-compose.yml (add training service)

services:
  # ... existing services ...

  # Continuous ML training
  ml-trainer:
    build: .
    command: python scripts/continuous_training.py --config config/ml/btc_lstm_config.yaml
    environment:
      TRAINING_MODE: "continuous"
    volumes:
      - ./data:/app/data # Shared database
      - ./models:/app/models # Model storage
      - ./logs:/app/logs
    restart: unless-stopped
```

### Training Workflow

1. **Initial Training** (one-time):

   ```bash
   python scripts/train_model.py --config config/ml/btc_lstm_config.yaml --mode train
   ```

2. **Evaluate Model**:

   ```bash
   python scripts/train_model.py --config config/ml/btc_lstm_config.yaml --mode evaluate
   ```

3. **Deploy to Production**:

   ```bash
   python scripts/train_model.py --config config/ml/btc_lstm_config.yaml --mode deploy
   ```

4. **Continuous Training** (rolling window):
   ```bash
   docker compose up ml-trainer
   # Automatically retrains daily using last 30 days of data
   ```

### Key Benefits

1. ✅ **Rolling Window** - Always trains on recent market conditions
2. ✅ **Historical + Live** - Database contains both, no distinction needed
3. ✅ **Continuous Learning** - Automatically adapts to market changes
4. ✅ **Backtesting** - Validate before deployment
5. ✅ **Versioning** - Track model performance over time
6. ✅ **Hot-Swap** - Deploy new models without downtime
7. ✅ **Configurable** - All settings in YAML

### Data Flow

```
Historical Data (backfiller) ─┐
                              ├─→ SQLite Database ─→ Training Script ─→ New Model
Live Data (websocket) ────────┘                                              ↓
                                                                              ↓
                                                                    Strategy Uses Model
```

The database acts as a unified data lake - doesn't matter if data came from REST API (historical) or WebSocket (live). Training script just queries the last N days.

## True VWAP Using Trades Stream

### Why True VWAP?

**Traditional VWAP** (from OHLCV candles):

- Uses average price from candles (e.g., `(high + low + close) / 3`)
- Approximates volume distribution within candle
- Not based on actual trade execution prices

**True VWAP** (from trades stream):

- Uses actual trade execution prices
- Weights each individual trade by its volume
- More accurate representation of average price paid

### Formula

```
VWAP = Σ(Trade_Price × Trade_Volume) / Σ(Trade_Volume)
```

Where each trade is an individual execution captured by our WebSocket.

### Implementation

```
packages/
  indicators/
    conventional/
      vwap_true/
        __init__.py
        main.py           # True VWAP calculation
        utils/
          helpers.py      # Time window utilities
```

### Core Implementation

```python
# packages/indicators/conventional/vwap_true/main.py

from datetime import datetime, timedelta
import pandas as pd
from typing import Optional, Literal

class TrueVWAP:
    """
    Calculate true Volume Weighted Average Price from actual trades.

    Uses trades table from WebSocket capture, not OHLCV candles.
    """

    def __init__(self, db_connection):
        self.db = db_connection

    def calculate(
        self,
        exchange: str,
        symbol: str,
        window_type: Literal['session', 'rolling', 'anchored'] = 'session',
        window_size_minutes: Optional[int] = None,
        anchor_time: Optional[datetime] = None,
        current_time: Optional[datetime] = None
    ) -> float:
        """
        Calculate true VWAP from trades.

        Args:
            exchange: Exchange name (e.g., 'mexc')
            symbol: Trading pair (e.g., 'BTC/USDT')
            window_type:
                - 'session': Since start of trading session (default: midnight UTC)
                - 'rolling': Last N minutes
                - 'anchored': From specific timestamp
            window_size_minutes: Required for 'rolling' mode
            anchor_time: Required for 'anchored' mode
            current_time: End time (default: now)

        Returns:
            VWAP value (float)
        """
        if current_time is None:
            current_time = datetime.utcnow()

        # Determine start time based on window type
        start_time = self._get_start_time(
            window_type,
            window_size_minutes,
            anchor_time,
            current_time
        )

        # Query trades from database
        query = """
        SELECT price, amount
        FROM trades_data
        WHERE exchange = ?
          AND symbol = ?
          AND timestamp >= ?
          AND timestamp <= ?
        ORDER BY timestamp ASC
        """

        df = pd.read_sql(
            query,
            self.db,
            params=[
                exchange,
                symbol,
                int(start_time.timestamp()),
                int(current_time.timestamp())
            ]
        )

        if df.empty:
            return None

        # Calculate true VWAP
        df['dollar_volume'] = df['price'] * df['amount']

        vwap = df['dollar_volume'].sum() / df['amount'].sum()

        return vwap

    def calculate_with_bands(
        self,
        exchange: str,
        symbol: str,
        std_dev: float = 2.0,
        **kwargs
    ) -> dict:
        """
        Calculate VWAP with standard deviation bands.

        Returns:
            {
                'vwap': float,
                'upper_band': float,
                'lower_band': float,
                'std_dev': float
            }
        """
        # Get start time
        if kwargs.get('current_time') is None:
            kwargs['current_time'] = datetime.utcnow()

        start_time = self._get_start_time(
            kwargs.get('window_type', 'session'),
            kwargs.get('window_size_minutes'),
            kwargs.get('anchor_time'),
            kwargs['current_time']
        )

        # Query trades
        query = """
        SELECT price, amount, timestamp
        FROM trades_data
        WHERE exchange = ?
          AND symbol = ?
          AND timestamp >= ?
          AND timestamp <= ?
        ORDER BY timestamp ASC
        """

        df = pd.read_sql(
            query,
            self.db,
            params=[
                exchange,
                symbol,
                int(start_time.timestamp()),
                int(kwargs['current_time'].timestamp())
            ]
        )

        if df.empty:
            return None

        # Calculate VWAP
        df['dollar_volume'] = df['price'] * df['amount']
        vwap = df['dollar_volume'].sum() / df['amount'].sum()

        # Calculate standard deviation (volume-weighted)
        df['squared_diff'] = df['amount'] * ((df['price'] - vwap) ** 2)
        variance = df['squared_diff'].sum() / df['amount'].sum()
        std = variance ** 0.5

        return {
            'vwap': vwap,
            'upper_band': vwap + (std_dev * std),
            'lower_band': vwap - (std_dev * std),
            'std_dev': std
        }

    def calculate_continuous(
        self,
        exchange: str,
        symbol: str,
        timeframe: str = '1m',
        window_type: str = 'session',
        **kwargs
    ) -> pd.DataFrame:
        """
        Calculate VWAP values for each candle in timeframe.

        Useful for historical analysis and backtesting.

        Returns:
            DataFrame with columns: timestamp, vwap, upper_band, lower_band
        """
        # Get all candles in requested period
        # For each candle, calculate VWAP up to that point
        # This creates a time series of VWAP values

        pass  # Implementation similar to above

    def _get_start_time(
        self,
        window_type: str,
        window_size_minutes: Optional[int],
        anchor_time: Optional[datetime],
        current_time: datetime
    ) -> datetime:
        """Calculate start time based on window type."""

        if window_type == 'session':
            # Start of current trading session (midnight UTC)
            return current_time.replace(hour=0, minute=0, second=0, microsecond=0)

        elif window_type == 'rolling':
            if window_size_minutes is None:
                raise ValueError("window_size_minutes required for rolling window")
            return current_time - timedelta(minutes=window_size_minutes)

        elif window_type == 'anchored':
            if anchor_time is None:
                raise ValueError("anchor_time required for anchored window")
            return anchor_time

        else:
            raise ValueError(f"Unknown window_type: {window_type}")


# Convenience functions
def calculate_vwap(
    db_connection,
    exchange: str,
    symbol: str,
    window_minutes: int = 60
) -> float:
    """
    Calculate true VWAP over rolling window.

    Quick helper for common use case.
    """
    calculator = TrueVWAP(db_connection)
    return calculator.calculate(
        exchange=exchange,
        symbol=symbol,
        window_type='rolling',
        window_size_minutes=window_minutes
    )


def calculate_session_vwap(
    db_connection,
    exchange: str,
    symbol: str
) -> float:
    """
    Calculate VWAP since start of trading session.
    """
    calculator = TrueVWAP(db_connection)
    return calculator.calculate(
        exchange=exchange,
        symbol=symbol,
        window_type='session'
    )
```

### Usage in Strategies

```python
# In strategy's on_candle() method

from packages.indicators.conventional.vwap_true.main import TrueVWAP

class VWAPStrategy(BaseStrategy):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.vwap_calculator = TrueVWAP(self.db_connection)

    def on_candle(self, candle: Dict[str, float], timeframe: str) -> Optional[List[Signal]]:
        """Generate signals based on true VWAP."""

        # Calculate session VWAP
        vwap = self.vwap_calculator.calculate(
            exchange=self.exchange,
            symbol=self.symbol,
            window_type='session'
        )

        # Get VWAP with bands
        vwap_data = self.vwap_calculator.calculate_with_bands(
            exchange=self.exchange,
            symbol=self.symbol,
            window_type='session',
            std_dev=2.0
        )

        current_price = candle['close']

        # Strategy logic
        signals = []

        # Buy when price below VWAP (potential reversion)
        if current_price < vwap_data['lower_band']:
            signals.append(Signal(
                type=SignalType.BUY,
                source=SignalSource.TECHNICAL,
                confidence=0.8,
                reason=f"Price ${current_price:.2f} below VWAP lower band ${vwap_data['lower_band']:.2f}",
                metadata={
                    'vwap': vwap_data['vwap'],
                    'upper_band': vwap_data['upper_band'],
                    'lower_band': vwap_data['lower_band'],
                    'distance_from_vwap': ((current_price - vwap_data['vwap']) / vwap_data['vwap']) * 100
                }
            ))

        # Sell when price above VWAP
        elif current_price > vwap_data['upper_band']:
            signals.append(Signal(
                type=SignalType.SELL,
                source=SignalSource.TECHNICAL,
                confidence=0.8,
                reason=f"Price ${current_price:.2f} above VWAP upper band ${vwap_data['upper_band']:.2f}"
            ))

        return signals if signals else None
```

### YAML Configuration

```yaml
# config/strategies/btc_vwap_strategy.yaml

strategy:
  id: "btc-vwap-001"
  name: "BTC True VWAP Mean Reversion"
  class: "VWAPStrategy"

market:
  exchange: "mexc"
  symbol: "BTC/USDT"
  primary_timeframe: "1m"

parameters:
  # VWAP settings
  vwap_window_type: "session" # session | rolling | anchored
  vwap_rolling_minutes: 60 # For rolling window
  vwap_std_dev: 2.0 # Standard deviation bands

  # Entry signals
  entry_below_lower_band: true # Buy below lower band
  entry_above_upper_band: false # Sell above upper band (set true for shorting)

  # Exit signals
  exit_at_vwap: true # Close when price returns to VWAP

  position_size_pct: 2.0
  max_position_size: 0.1

exits:
  stop_loss_pct: 1.0
  take_profit_pct: 2.0
  trailing_stop_pct: 0.5
```

### ML Feature Integration

Add true VWAP as a feature for ML models:

```yaml
# config/ml/btc_lstm_config.yaml

features:
  # ... existing features ...

  # True VWAP features
  vwap_features:
    - name: "session_vwap"
      window_type: "session"

    - name: "rolling_vwap_60m"
      window_type: "rolling"
      window_minutes: 60

    - name: "rolling_vwap_15m"
      window_type: "rolling"
      window_minutes: 15

    # Distance from VWAP (normalized)
    - name: "vwap_distance_pct"
      calculation: "(price - vwap) / vwap * 100"

    # VWAP bands
    - name: "vwap_upper_band"
      std_dev: 2.0

    - name: "vwap_lower_band"
      std_dev: 2.0

    # VWAP position (0-1 scale)
    - name: "vwap_position"
      calculation: "(price - lower_band) / (upper_band - lower_band)"
```

### Feature Engineering Updates

```python
# packages/ml/feature_engineering.py

def _add_vwap_features(self, df: pd.DataFrame) -> pd.DataFrame:
    """Add true VWAP features."""
    from packages.indicators.conventional.vwap_true.main import TrueVWAP

    vwap_calc = TrueVWAP(self.db_connection)

    for feature in self.config['features'].get('vwap_features', []):
        name = feature['name']

        if feature['window_type'] == 'session':
            # Calculate session VWAP for each row
            vwap_values = []
            for timestamp in df.index:
                vwap = vwap_calc.calculate(
                    exchange=self.config['data']['exchange'],
                    symbol=self.config['data']['symbol'],
                    window_type='session',
                    current_time=timestamp
                )
                vwap_values.append(vwap)

            df[name] = vwap_values

        elif feature['window_type'] == 'rolling':
            window_minutes = feature['window_minutes']

            vwap_values = []
            for timestamp in df.index:
                vwap = vwap_calc.calculate(
                    exchange=self.config['data']['exchange'],
                    symbol=self.config['data']['symbol'],
                    window_type='rolling',
                    window_size_minutes=window_minutes,
                    current_time=timestamp
                )
                vwap_values.append(vwap)

            df[name] = vwap_values

    # Calculate derived features
    if 'vwap_distance_pct' in [f['name'] for f in self.config['features'].get('vwap_features', [])]:
        df['vwap_distance_pct'] = ((df['close'] - df['session_vwap']) / df['session_vwap']) * 100

    return df
```

### Example: True VWAP vs Traditional VWAP

```python
# Comparison script

from packages.indicators.conventional.vwap_true.main import calculate_session_vwap
from packages.indicators.conventional.vwap import calculate_vwap  # Traditional

# True VWAP (from trades)
true_vwap = calculate_session_vwap(db, 'mexc', 'BTC/USDT')
# Result: $42,156.32

# Traditional VWAP (from OHLCV)
candles = fetch_ohlcv(...)
traditional_vwap = calculate_vwap(candles, period=1440)  # Full day
# Result: $42,148.75

# Difference
diff = true_vwap - traditional_vwap
# Result: +$7.57 (0.018%)

# Why the difference?
# - True VWAP weighs each trade by its actual execution volume
# - Traditional VWAP uses candle typical price ((H+L+C)/3) × candle volume
# - True VWAP reflects actual market participant behavior more accurately
```

### Console Output Example

```
[10:30:00] 📊 VWAP Analysis:
           True VWAP:        $42,156.32
           Current Price:    $42,089.50
           Distance:         -0.16% (below VWAP)

           VWAP Bands:
           ├─ Upper (+2σ):   $42,312.18
           ├─ VWAP:          $42,156.32
           └─ Lower (-2σ):   $42,000.46

           Position:         Price in lower quartile
           Signal:           🟢 BUY (mean reversion setup)

           Session Stats:
           ├─ Trades:        15,234 executions
           ├─ Volume:        284.5 BTC
           ├─ High:          $42,450.00
           └─ Low:           $41,950.00
```

### Benefits of True VWAP

1. ✅ **Accuracy**: Uses actual trade executions, not candle approximations
2. ✅ **Real-time**: Updates with every trade from WebSocket
3. ✅ **Institutional**: Matches how institutional traders calculate VWAP
4. ✅ **Volume Profile**: Captures true volume distribution
5. ✅ **Mean Reversion**: Better support/resistance levels
6. ✅ **ML Features**: More informative features for models

### Database Schema Update (Already Exists!)

Our `trades_data` table (from WebSocket) already has everything we need:

```sql
CREATE TABLE trades_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timestamp INTEGER NOT NULL,      -- Trade execution time
    price REAL NOT NULL,             -- Actual execution price
    amount REAL NOT NULL,            -- Trade volume
    side TEXT,                       -- buy | sell
    trade_id TEXT,

    UNIQUE(exchange, symbol, timestamp, trade_id)
);
```

No schema changes needed - we already capture all required data! 🎉

### Performance Optimization

For strategies running on 1m timeframe with thousands of trades:

```python
# Cache VWAP within candle period
class VWAPStrategy(BaseStrategy):
    def __init__(self, config):
        super().__init__(config)
        self.vwap_calculator = TrueVWAP(self.db_connection)
        self.vwap_cache = {}
        self.cache_timestamp = None

    def on_candle(self, candle: Dict, timeframe: str):
        current_minute = candle['timestamp'] // 60000  # Floor to minute

        # Only recalculate VWAP once per minute
        if self.cache_timestamp != current_minute:
            self.vwap_cache = self.vwap_calculator.calculate_with_bands(
                exchange=self.exchange,
                symbol=self.symbol,
                window_type='session',
                std_dev=2.0
            )
            self.cache_timestamp = current_minute

        # Use cached VWAP for this candle
        vwap_data = self.vwap_cache
        # ... strategy logic ...
```

### Summary

True VWAP leverages our WebSocket trades stream to calculate the real volume-weighted average price - not an approximation from candles. This gives us:

- **Institutional-grade accuracy** for support/resistance levels
- **Real-time updates** as each trade executes
- **Better ML features** reflecting actual market behavior
- **Mean reversion signals** based on true volume distribution

Implementation is straightforward since we already capture all trade data via WebSocket. Just query `trades_data` table and apply the formula!

## Next Steps

1. Implement `packages/execution/manager.py` (order execution)
2. Implement `packages/strategies/base.py` (base strategy class)
3. Implement `packages/strategies/loader.py` (dynamic loading)
4. Create example strategy: `RSIMeanReversion`
5. Build `apps/trader/runtime.py` (trading loop)
6. Test in paper mode
7. Add Prometheus integration
8. Deploy to production (live mode)
