"""
Prometheus metrics for real-time monitoring.

Exports metrics to Prometheus Pushgateway for Grafana visualization.
"""

import os
from typing import Optional
from prometheus_client import Gauge, Counter, Histogram, CollectorRegistry, push_to_gateway
from packages.logging.logger import setup_logger

logger = setup_logger(__name__)


class PrometheusMetrics:
    """
    Prometheus metrics manager for trading bot.
    
    Provides sub-second updates for Grafana dashboards via Pushgateway.
    """
    
    def __init__(self, exchange: str, pushgateway_url: Optional[str] = None):
        """
        Initialize Prometheus metrics.
        
        Args:
            exchange: Exchange name (e.g., 'binance', 'mexc')
            pushgateway_url: Pushgateway URL (default: http://pushgateway:9091)
        """
        self.exchange = exchange
        self.pushgateway_url = pushgateway_url or os.getenv(
            'PROMETHEUS_PUSHGATEWAY',
            'http://pushgateway:9091'
        )
        
        # Create separate registry to avoid conflicts
        self.registry = CollectorRegistry()
        
        # ===== Price Metrics =====
        self.price_gauge = Gauge(
            'crypto_price',
            'Current price',
            ['exchange', 'symbol', 'type'],  # type: last, bid, ask
            registry=self.registry
        )
        
        # ===== Trade Metrics =====
        self.trade_counter = Counter(
            'crypto_trades_total',
            'Total trades',
            ['exchange', 'symbol', 'side'],  # side: buy, sell
            registry=self.registry
        )
        
        self.trade_volume = Gauge(
            'crypto_trade_volume',
            'Recent trade volume (rolling)',
            ['exchange', 'symbol'],
            registry=self.registry
        )
        
        self.trade_size_histogram = Histogram(
            'crypto_trade_size',
            'Trade size distribution',
            ['exchange', 'symbol'],
            buckets=[0.001, 0.01, 0.1, 1, 10, 100, 1000],
            registry=self.registry
        )
        
        # ===== Candle Metrics (Current Forming Candle) =====
        self.candle_open = Gauge(
            'crypto_candle_open',
            'Current candle open',
            ['exchange', 'symbol', 'timeframe'],
            registry=self.registry
        )
        
        self.candle_high = Gauge(
            'crypto_candle_high',
            'Current candle high',
            ['exchange', 'symbol', 'timeframe'],
            registry=self.registry
        )
        
        self.candle_low = Gauge(
            'crypto_candle_low',
            'Current candle low',
            ['exchange', 'symbol', 'timeframe'],
            registry=self.registry
        )
        
        self.candle_close = Gauge(
            'crypto_candle_close',
            'Current candle close (last price)',
            ['exchange', 'symbol', 'timeframe'],
            registry=self.registry
        )
        
        self.candle_volume = Gauge(
            'crypto_candle_volume',
            'Current candle volume',
            ['exchange', 'symbol', 'timeframe'],
            registry=self.registry
        )
        
        # ===== Orderbook Metrics =====
        self.orderbook_spread = Gauge(
            'crypto_spread',
            'Bid-ask spread',
            ['exchange', 'symbol'],
            registry=self.registry
        )
        
        self.orderbook_bid_price = Gauge(
            'crypto_orderbook_bid_price',
            'Order book bid price by level',
            ['exchange', 'symbol', 'level'],
            registry=self.registry
        )
        
        self.orderbook_ask_price = Gauge(
            'crypto_orderbook_ask_price',
            'Order book ask price by level',
            ['exchange', 'symbol', 'level'],
            registry=self.registry
        )
        
        self.orderbook_bid_quantity = Gauge(
            'crypto_orderbook_bid_quantity',
            'Order book bid quantity by level',
            ['exchange', 'symbol', 'level'],
            registry=self.registry
        )
        
        self.orderbook_ask_quantity = Gauge(
            'crypto_orderbook_ask_quantity',
            'Order book ask quantity by level',
            ['exchange', 'symbol', 'level'],
            registry=self.registry
        )
        
        self.orderbook_bid_cumulative = Gauge(
            'crypto_orderbook_bid_cumulative',
            'Cumulative bid quantity (for depth chart)',
            ['exchange', 'symbol', 'level'],
            registry=self.registry
        )
        
        self.orderbook_ask_cumulative = Gauge(
            'crypto_orderbook_ask_cumulative',
            'Cumulative ask quantity (for depth chart)',
            ['exchange', 'symbol', 'level'],
            registry=self.registry
        )
        
        self.orderbook_total_bids = Gauge(
            'crypto_orderbook_total_bids',
            'Total bid liquidity (approximate USD value)',
            ['exchange', 'symbol'],
            registry=self.registry
        )
        
        self.orderbook_total_asks = Gauge(
            'crypto_orderbook_total_asks',
            'Total ask liquidity (approximate USD value)',
            ['exchange', 'symbol'],
            registry=self.registry
        )
        
        # ===== Strategy Metrics =====
        self.strategy_signals = Counter(
            'strategy_signals_total',
            'Total signals generated',
            ['strategy_id', 'signal_type'],  # signal_type: LONG, SHORT, EXIT
            registry=self.registry
        )
        
        self.strategy_position_size = Gauge(
            'strategy_position_size',
            'Current position size',
            ['strategy_id', 'symbol'],
            registry=self.registry
        )
        
        self.strategy_pnl = Gauge(
            'strategy_pnl',
            'Current PNL',
            ['strategy_id', 'symbol'],
            registry=self.registry
        )
        
        self.strategy_trades = Counter(
            'strategy_trades_total',
            'Total trades executed',
            ['strategy_id', 'side'],  # side: buy, sell
            registry=self.registry
        )
        
        # ===== Performance Metrics =====
        self.websocket_latency = Histogram(
            'websocket_latency_seconds',
            'WebSocket message latency',
            ['exchange', 'stream_type'],
            buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
            registry=self.registry
        )
        
        logger.info(f"Initialized Prometheus metrics for {exchange}")
    
    def update_price(self, symbol: str, last: float, bid: float = None, ask: float = None):
        """Update current price metrics."""
        self.price_gauge.labels(self.exchange, symbol, 'last').set(last)
        if bid is not None:
            self.price_gauge.labels(self.exchange, symbol, 'bid').set(bid)
        if ask is not None:
            self.price_gauge.labels(self.exchange, symbol, 'ask').set(ask)
    
    def record_trade(self, symbol: str, side: str, amount: float, price: float):
        """Record a trade event."""
        self.trade_counter.labels(self.exchange, symbol, side).inc()
        self.trade_size_histogram.labels(self.exchange, symbol).observe(amount)
    
    def update_candle(self, symbol: str, timeframe: str, open_: float, high: float, 
                     low: float, close: float, volume: float):
        """Update current forming candle metrics."""
        self.candle_open.labels(self.exchange, symbol, timeframe).set(open_)
        self.candle_high.labels(self.exchange, symbol, timeframe).set(high)
        self.candle_low.labels(self.exchange, symbol, timeframe).set(low)
        self.candle_close.labels(self.exchange, symbol, timeframe).set(close)
        self.candle_volume.labels(self.exchange, symbol, timeframe).set(volume)
    
    def update_orderbook(self, symbol: str, bids: list, asks: list, depth: int = 10):
        """
        Update orderbook metrics.
        
        Args:
            symbol: Trading pair
            bids: List of [price, amount] bid levels
            asks: List of [price, amount] ask levels
            depth: Number of levels to track (default 10)
        """
        if not bids or not asks:
            return
        
        # Spread
        spread = asks[0][0] - bids[0][0]
        self.orderbook_spread.labels(self.exchange, symbol).set(spread)
        
        # Process bids
        bid_cumulative = 0
        bid_value = 0
        for i, (price, amount) in enumerate(bids[:depth]):
            bid_cumulative += amount
            bid_value += amount * price
            
            self.orderbook_bid_price.labels(self.exchange, symbol, str(i)).set(price)
            self.orderbook_bid_quantity.labels(self.exchange, symbol, str(i)).set(amount)
            self.orderbook_bid_cumulative.labels(self.exchange, symbol, str(i)).set(bid_cumulative)
        
        # Process asks
        ask_cumulative = 0
        ask_value = 0
        for i, (price, amount) in enumerate(asks[:depth]):
            ask_cumulative += amount
            ask_value += amount * price
            
            self.orderbook_ask_price.labels(self.exchange, symbol, str(i)).set(price)
            self.orderbook_ask_quantity.labels(self.exchange, symbol, str(i)).set(amount)
            self.orderbook_ask_cumulative.labels(self.exchange, symbol, str(i)).set(ask_cumulative)
        
        # Totals
        self.orderbook_total_bids.labels(self.exchange, symbol).set(bid_value)
        self.orderbook_total_asks.labels(self.exchange, symbol).set(ask_value)
    
    def record_signal(self, strategy_id: str, signal_type: str):
        """Record strategy signal."""
        self.strategy_signals.labels(strategy_id, signal_type).inc()
    
    def update_position(self, strategy_id: str, symbol: str, size: float, pnl: float):
        """Update strategy position metrics."""
        self.strategy_position_size.labels(strategy_id, symbol).set(size)
        self.strategy_pnl.labels(strategy_id, symbol).set(pnl)
    
    def record_strategy_trade(self, strategy_id: str, side: str):
        """Record strategy trade execution."""
        self.strategy_trades.labels(strategy_id, side).inc()
    
    def record_latency(self, stream_type: str, latency_seconds: float):
        """Record WebSocket latency."""
        self.websocket_latency.labels(self.exchange, stream_type).observe(latency_seconds)
    
    def push(self):
        """Push all metrics to Pushgateway."""
        try:
            push_to_gateway(
                self.pushgateway_url,
                job=f'trading_bot_{self.exchange}',
                registry=self.registry
            )
        except Exception as e:
            logger.warning(f"Failed to push metrics to Pushgateway: {e}")


def push_metrics(metrics: PrometheusMetrics):
    """
    Convenience function to push metrics.
    
    Args:
        metrics: PrometheusMetrics instance
    """
    metrics.push()
