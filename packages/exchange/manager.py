"""
Exchange manager for CCXT abstraction.

Centralizes exchange initialization, API credential management,
and common exchange operations to maintain DRY principles.
"""

import os
from typing import Optional, Dict, Any, List
import ccxt
from packages.logging.logger import setup_logger

logger = setup_logger(__name__)


class ExchangeManager:
    """
    Manages exchange connections and common operations.
    
    Responsibilities:
    - Initialize CCXT exchange instances
    - Load API credentials from environment
    - Provide unified interface for exchange operations
    - Handle exchange-specific quirks
    """
    
    def __init__(
        self,
        exchange_name: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        sandbox: bool = False,
        enable_rate_limit: bool = True,
    ):
        """
        Initialize exchange manager.
        
        Args:
            exchange_name: Exchange name (e.g., 'mexc', 'binance')
            api_key: API key (loaded from env if not provided)
            api_secret: API secret (loaded from env if not provided)
            sandbox: Use sandbox/testnet mode
            enable_rate_limit: Enable CCXT rate limiting
        """
        self.exchange_name = exchange_name.lower()
        self.sandbox = sandbox
        
        # Load API credentials
        if api_key is None:
            api_key = os.getenv(f"{exchange_name.upper()}_API_KEY")
        if api_secret is None:
            api_secret = os.getenv(f"{exchange_name.upper()}_API_SECRET")
        
        if not api_key or not api_secret:
            raise ValueError(
                f"API credentials required for {exchange_name}. "
                f"Set {exchange_name.upper()}_API_KEY and {exchange_name.upper()}_API_SECRET"
            )
        
        # Initialize exchange
        try:
            exchange_class = getattr(ccxt, exchange_name)
        except AttributeError:
            raise ValueError(f"Exchange '{exchange_name}' not supported by CCXT")
        
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': enable_rate_limit,
        })
        
        # Enable sandbox mode if requested
        if sandbox:
            if hasattr(self.exchange, 'set_sandbox_mode'):
                self.exchange.set_sandbox_mode(True)
                logger.info(f"{exchange_name} sandbox mode enabled")
            else:
                logger.warning(f"{exchange_name} does not support sandbox mode")
        
        logger.info(f"ExchangeManager initialized for {exchange_name}")
    
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1m',
        since: Optional[int] = None,
        limit: int = 500,
    ) -> List[List]:
        """
        Fetch OHLCV data from exchange.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Timeframe (e.g., '1m', '1h', '1d')
            since: Start timestamp in milliseconds
            limit: Max number of candles
            
        Returns:
            List of OHLCV arrays [[timestamp, open, high, low, close, volume], ...]
        """
        return self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
    
    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current ticker data.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Ticker dictionary with bid, ask, last, volume, etc.
        """
        return self.exchange.fetch_ticker(symbol)
    
    def fetch_balance(self) -> Dict[str, Any]:
        """
        Fetch account balance.
        
        Returns:
            Balance dictionary with free/used/total for each currency
        """
        return self.exchange.fetch_balance()
    
    def create_market_buy_order(
        self, symbol: str, amount: float
    ) -> Dict[str, Any]:
        """
        Place market buy order.
        
        Args:
            symbol: Trading pair
            amount: Amount to buy (in base currency)
            
        Returns:
            Order info dictionary
        """
        return self.exchange.create_market_buy_order(symbol, amount)
    
    def create_market_sell_order(
        self, symbol: str, amount: float
    ) -> Dict[str, Any]:
        """
        Place market sell order.
        
        Args:
            symbol: Trading pair
            amount: Amount to sell (in base currency)
            
        Returns:
            Order info dictionary
        """
        return self.exchange.create_market_sell_order(symbol, amount)
    
    def create_limit_buy_order(
        self, symbol: str, amount: float, price: float
    ) -> Dict[str, Any]:
        """
        Place limit buy order.
        
        Args:
            symbol: Trading pair
            amount: Amount to buy
            price: Limit price
            
        Returns:
            Order info dictionary
        """
        return self.exchange.create_limit_buy_order(symbol, amount, price)
    
    def create_limit_sell_order(
        self, symbol: str, amount: float, price: float
    ) -> Dict[str, Any]:
        """
        Place limit sell order.
        
        Args:
            symbol: Trading pair
            amount: Amount to sell
            price: Limit price
            
        Returns:
            Order info dictionary
        """
        return self.exchange.create_limit_sell_order(symbol, amount, price)
    
    def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID
            symbol: Trading pair
            
        Returns:
            Cancelled order info
        """
        return self.exchange.cancel_order(order_id, symbol)
    
    def fetch_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Fetch order status.
        
        Args:
            order_id: Order ID
            symbol: Trading pair
            
        Returns:
            Order info dictionary
        """
        return self.exchange.fetch_order(order_id, symbol)
    
    def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch open orders.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            List of open orders
        """
        return self.exchange.fetch_open_orders(symbol)
    
    def fetch_closed_orders(
        self, symbol: Optional[str] = None, since: Optional[int] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch closed orders.
        
        Args:
            symbol: Optional symbol filter
            since: Optional start timestamp
            limit: Max number of orders
            
        Returns:
            List of closed orders
        """
        return self.exchange.fetch_closed_orders(symbol, since, limit)
    
    def fetch_markets(self) -> List[Dict[str, Any]]:
        """
        Fetch available markets.
        
        Returns:
            List of market information dictionaries
        """
        return self.exchange.fetch_markets()
    
    def get_timeframe_duration_ms(self, timeframe: str) -> int:
        """
        Get timeframe duration in milliseconds.
        
        Args:
            timeframe: Timeframe string (e.g., '1m', '1h')
            
        Returns:
            Duration in milliseconds
        """
        return self.exchange.parse_timeframe(timeframe) * 1000
    
    def load_markets(self):
        """Load market metadata from exchange."""
        self.exchange.load_markets()
        logger.info(f"Loaded {len(self.exchange.markets)} markets from {self.exchange_name}")
    
    @property
    def has_sandbox(self) -> bool:
        """Check if exchange supports sandbox mode."""
        return hasattr(self.exchange, 'set_sandbox_mode')
    
    @property
    def has_websocket(self) -> bool:
        """Check if exchange supports WebSocket."""
        return hasattr(self.exchange, 'watch_ticker')
    
    def close(self):
        """Close exchange connection."""
        if hasattr(self.exchange, 'close'):
            self.exchange.close()


def get_exchange_manager(
    exchange_name: str,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    sandbox: bool = False,
) -> ExchangeManager:
    """
    Factory function to create ExchangeManager.
    
    Args:
        exchange_name: Exchange name
        api_key: API key (from env if None)
        api_secret: API secret (from env if None)
        sandbox: Use sandbox mode
        
    Returns:
        ExchangeManager instance
    """
    return ExchangeManager(
        exchange_name=exchange_name,
        api_key=api_key,
        api_secret=api_secret,
        sandbox=sandbox,
    )
