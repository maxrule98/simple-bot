"""
Example: Integrating Prometheus metrics into WebSocket manager.

This shows how to add real-time metrics to the websocket package.
"""

from packages.metrics import PrometheusMetrics
import time

class WebSocketManagerWithMetrics:
    """Example of WebSocket manager with Prometheus metrics integrated."""
    
    def __init__(self, exchange_name: str, symbols: list):
        self.exchange_name = exchange_name
        self.symbols = symbols
        
        # Initialize Prometheus metrics
        self.metrics = PrometheusMetrics(exchange=exchange_name)
        
        # Push metrics every 2 seconds
        self.last_push = time.time()
        self.push_interval = 2.0  # seconds
    
    async def _on_ticker(self, ticker: dict, symbol: str):
        """Handle ticker updates with metrics."""
        # Update Prometheus metrics
        self.metrics.update_price(
            symbol=symbol,
            last=ticker['last'],
            bid=ticker['bid'],
            ask=ticker['ask']
        )
        
        # Store in database (existing code)
        # ...
        
        # Push to Pushgateway periodically
        await self._maybe_push()
    
    async def _on_ohlcv(self, ohlcv: dict, symbol: str, timeframe: str):
        """Handle OHLCV updates with metrics."""
        # Update Prometheus candle metrics
        self.metrics.update_candle(
            symbol=symbol,
            timeframe=timeframe,
            open_=ohlcv['open'],
            high=ohlcv['high'],
            low=ohlcv['low'],
            close=ohlcv['close'],
            volume=ohlcv['volume']
        )
        
        # Store in database (existing code)
        # ...
        
        await self._maybe_push()
    
    async def _on_trade(self, trade: dict, symbol: str):
        """Handle trade updates with metrics."""
        start_time = time.time()
        
        # Record trade
        self.metrics.record_trade(
            symbol=symbol,
            side=trade['side'],
            amount=trade['amount'],
            price=trade['price']
        )
        
        # Record latency
        latency = time.time() - start_time
        self.metrics.record_latency('trade', latency)
        
        # Store in database (existing code)
        # ...
        
        await self._maybe_push()
    
    async def _on_orderbook(self, orderbook: dict, symbol: str):
        """Handle orderbook updates with metrics."""
        start_time = time.time()
        
        # Update orderbook metrics (10 levels for depth chart)
        self.metrics.update_orderbook(
            symbol=symbol,
            bids=orderbook.get('bids', []),
            asks=orderbook.get('asks', []),
            depth=10
        )
        
        # Record latency
        latency = time.time() - start_time
        self.metrics.record_latency('orderbook', latency)
        
        # Store in database (existing code)
        # ...
        
        await self._maybe_push()
    
    async def _maybe_push(self):
        """Push metrics to Pushgateway if interval elapsed."""
        now = time.time()
        if now - self.last_push >= self.push_interval:
            self.metrics.push()
            self.last_push = now


# Example: Strategy metrics integration
class YAMLStrategyWithMetrics:
    """Example strategy with Prometheus metrics."""
    
    def __init__(self, strategy_id: str, exchange: str):
        self.strategy_id = strategy_id
        self.metrics = PrometheusMetrics(exchange=exchange)
    
    def generate_signals(self, candle: dict) -> dict:
        """Generate signals and record metrics."""
        # Strategy logic (existing code)
        signal = self._evaluate_conditions(candle)
        
        if signal['action'] != 'HOLD':
            # Record signal
            self.metrics.record_signal(
                strategy_id=self.strategy_id,
                signal_type=signal['action']  # LONG, SHORT, EXIT
            )
        
        return signal
    
    def on_trade_executed(self, trade: dict):
        """Record trade execution."""
        self.metrics.record_strategy_trade(
            strategy_id=self.strategy_id,
            side=trade['side']
        )
    
    def update_position(self, position: dict):
        """Update position metrics."""
        self.metrics.update_position(
            strategy_id=self.strategy_id,
            symbol=position['symbol'],
            size=position['size'],
            pnl=position['pnl']
        )
        
        # Push periodically
        self.metrics.push()
