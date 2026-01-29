"""
WebSocket data streaming for live trading.

Uses CCXT Pro for websocket connections to exchanges.
Streams real-time data and stores in same database tables as REST API data.

Key Features:
- Real-time OHLCV updates (1m candles updated as they form)
- Real-time ticker/price updates (bid, ask, last)
- Order book depth updates (bid/ask liquidity)
- Trade stream (optional)

Data Flow:
    Exchange WebSocket
        ↓
    CCXT Pro Handler
        ↓
    INSERT/UPDATE database
        ↓
    Same tables as REST data (ohlcv_data, ticker_data, orderbook_data)

Note: WebSocket data and REST data are identical structure,
      just different delivery mechanisms (push vs pull).
"""

import asyncio
import ccxt.pro as ccxt
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import time

from packages.logging.logger import setup_logger

# Get project root (2 levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class WebSocketManager:
    """
    Manages websocket connections for real-time market data.
    
    Uses CCXT Pro (requires: pip install ccxt[pro])
    """
    
    def __init__(
        self, 
        exchange_name: str, 
        symbols: List[str], 
        db_connection,
        orderbook_depth: int = 10
    ):
        """
        Initialize websocket manager.
        
        Args:
            exchange_name: Exchange to connect to (binance, coinbase, etc.)
            symbols: List of symbols to subscribe to
            db_connection: Database connection for storing data
            orderbook_depth: Number of price levels to capture (default: 10)
        """
        self.exchange_name = exchange_name
        self.symbols = symbols
        self.db = db_connection
        self.orderbook_depth = orderbook_depth
        self.exchange = None
        self.running = False
        self.candle_callback = None  # Optional callback for candle updates
        self.logger = setup_logger(f"websocket.{exchange_name}")
        
    async def connect(self):
        """Establish websocket connection to exchange."""
        exchange_class = getattr(ccxt, self.exchange_name)
        self.exchange = exchange_class({
            'enableRateLimit': True,
            # API keys loaded from environment if needed
        })
        print(f"✅ WebSocket connected to {self.exchange_name}")
        
    def register_candle_callback(self, callback):
        """
        Register callback for candle updates.
        
        Args:
            callback: Async function(candle: Dict, timeframe: str)
        """
        self.candle_callback = callback
        
    async def watch_ohlcv(self, symbol: str, timeframe: str = '1m'):
        """
        Stream OHLCV data for symbol/timeframe.
        
        Updates database in real-time as candles form.
        
        Args:
            symbol: Trading pair (BTC/USDT)
            timeframe: Candle timeframe (1m, 5m, 15m, etc.)
        """
        print(f"📊 Watching OHLCV: {symbol} {timeframe}")
        
        while self.running:
            try:
                # Watch for new candles
                ohlcv = await self.exchange.watch_ohlcv(symbol, timeframe)
                
                # Get most recent candle
                if ohlcv and len(ohlcv) > 0:
                    latest = ohlcv[-1]
                    timestamp, open_price, high, low, close, volume = latest
                    
                    # Insert or update in database (same table as REST data!)
                    self._store_ohlcv(
                        exchange=self.exchange_name,
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=timestamp,  # CCXT provides ms, store as-is
                        open=open_price,
                        high=high,
                        low=low,
                        close=close,
                        volume=volume
                    )
                    
                    # Call registered callback if exists
                    if self.candle_callback:
                        candle = {
                            "timestamp": timestamp,
                            "open": open_price,
                            "high": high,
                            "low": low,
                            "close": close,
                            "volume": volume,
                        }
                        await self.candle_callback(candle, timeframe)
                    
            except Exception as e:
                print(f"❌ Error watching OHLCV {symbol}: {e}")
                await asyncio.sleep(5)  # Wait before retry
                
    async def watch_ticker(self, symbol: str):
        """
        Stream real-time ticker/price updates.
        
        Updates database with latest bid/ask/last prices.
        
        Args:
            symbol: Trading pair (BTC/USDT)
        """
        print(f"💹 Watching ticker: {symbol}")
        
        while self.running:
            try:
                # Watch for price updates
                ticker = await self.exchange.watch_ticker(symbol)
                
                # Validate required fields
                bid = ticker.get('bid', 0) or 0
                ask = ticker.get('ask', 0) or 0
                last = ticker.get('last', 0) or ticker.get('close', 0) or 0
                volume_24h = ticker.get('quoteVolume', 0) or ticker.get('baseVolume', 0) or 0
                
                # Only store if we have a valid last price
                if last > 0:
                    self._store_ticker(
                        exchange=self.exchange_name,
                        symbol=symbol,
                        timestamp=int(time.time() * 1000),  # Convert seconds to ms
                        bid=bid,
                        ask=ask,
                        last=last,
                        volume_24h=volume_24h
                    )
                
            except Exception as e:
                print(f"❌ Error watching ticker {symbol}: {e}")
                await asyncio.sleep(5)
                
    async def watch_trades(self, symbol: str):
        """
        Stream individual trades for order flow analysis.
        
        Captures every trade executed on the exchange in real-time.
        Useful for:
        - Volume analysis
        - Order flow tracking
        - Whale activity detection
        - Price action confirmation
        
        Args:
            symbol: Trading pair (BTC/USDT)
        """
        print(f"💸 Watching trades: {symbol}")
        
        while self.running:
            try:
                trades = await self.exchange.watch_trades(symbol)
                
                # Store each trade
                for trade in trades:
                    # Generate unique trade_id if exchange doesn't provide one
                    # Use timestamp-price-amount to ensure uniqueness
                    trade_id = trade.get('id')
                    if trade_id is None or str(trade_id) == '' or str(trade_id) == 'None':
                        timestamp_ms = int(trade.get('timestamp', time.time() * 1000))
                        price = float(trade.get('price', 0))
                        amount = float(trade.get('amount', 0))
                        trade_id = f"{timestamp_ms}-{price:.8f}-{amount:.8f}"
                    else:
                        trade_id = str(trade_id)
                    
                    self._store_trade(
                        exchange=self.exchange_name,
                        symbol=trade.get('symbol', symbol),
                        trade_id=trade_id,
                        timestamp=int(trade.get('timestamp', time.time() * 1000)),  # CCXT provides ms
                        side=trade.get('side', 'unknown'),
                        price=trade.get('price', 0),
                        amount=trade.get('amount', 0),
                        cost=trade.get('cost', 0) or (trade.get('price', 0) * trade.get('amount', 0)),
                        taker_or_maker=trade.get('takerOrMaker'),
                        fee=trade.get('fee', {}).get('cost') if trade.get('fee') else None,
                        fee_currency=trade.get('fee', {}).get('currency') if trade.get('fee') else None
                    )
                    
            except Exception as e:
                print(f"❌ Error watching trades {symbol}: {e}")
                await asyncio.sleep(5)
                
    async def watch_order_book(self, symbol: str):
        """
        Stream real-time order book depth updates.
        
        Captures top N bids/asks for liquidity analysis.
        
        Args:
            symbol: Trading pair (BTC/USDT)
        """
        print(f"📚 Watching order book: {symbol} (depth: {self.orderbook_depth})")
        
        while self.running:
            try:
                # Watch for order book updates
                orderbook = await self.exchange.watch_order_book(symbol)
                
                # Extract top N bids and asks
                bids = orderbook.get('bids', [])[:self.orderbook_depth]
                asks = orderbook.get('asks', [])[:self.orderbook_depth]
                
                # Calculate derived metrics
                bid_ask_spread = None
                mid_price = None
                
                if bids and asks:
                    best_bid = bids[0][0]  # [price, amount]
                    best_ask = asks[0][0]
                    
                    # Sanity check: best ask should be >= best bid
                    # If not, the exchange might have inverted the arrays
                    if best_ask < best_bid:
                        # Swap bids and asks
                        bids, asks = asks, bids
                        best_bid, best_ask = best_ask, best_bid
                    
                    mid_price = (best_bid + best_ask) / 2
                    bid_ask_spread = best_ask - best_bid
                
                # Store in database
                self._store_orderbook(
                    exchange=self.exchange_name,
                    symbol=symbol,
                    timestamp=int(time.time() * 1000),  # Convert seconds to ms
                    bids=bids,
                    asks=asks,
                    bid_ask_spread=bid_ask_spread,
                    mid_price=mid_price
                )
                
            except Exception as e:
                print(f"❌ Error watching order book {symbol}: {e}")
                await asyncio.sleep(5)
                
    def _store_ohlcv(self, exchange: str, symbol: str, timeframe: str, 
                     timestamp: int, open: float, high: float, low: float, 
                     close: float, volume: float):
        """
        Store OHLCV data in database.
        
        Uses INSERT OR REPLACE to update candles as they form.
        """
        try:
            self.db.execute("""
                INSERT OR REPLACE INTO ohlcv_data
                (exchange, symbol, timeframe, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (exchange, symbol, timeframe, timestamp, open, high, low, close, volume))
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Error storing OHLCV: {e}")
            
    def _store_ticker(self, exchange: str, symbol: str, timestamp: int,
                      bid: float, ask: float, last: float, volume_24h: float):
        """Store ticker data in database."""
        try:
            self.db.execute("""
                INSERT OR REPLACE INTO ticker_data
                (exchange, symbol, timestamp, bid, ask, last, volume_24h)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (exchange, symbol, timestamp, bid, ask, last, volume_24h))
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Error storing ticker: {e}")
            
    def _store_orderbook(
        self, 
        exchange: str, 
        symbol: str, 
        timestamp: int,
        bids: List[List[float]], 
        asks: List[List[float]],
        bid_ask_spread: Optional[float],
        mid_price: Optional[float]
    ):
        """
        Store order book data in database.
        
        Stores bids/asks as JSON for flexible querying.
        
        Args:
            exchange: Exchange name
            symbol: Trading pair
            timestamp: Unix timestamp
            bids: List of [price, amount] pairs
            asks: List of [price, amount] pairs
            bid_ask_spread: Spread between best bid/ask
            mid_price: Mid-market price
        """
        try:
            # Convert bids/asks to JSON
            bids_json = json.dumps(bids)
            asks_json = json.dumps(asks)
            
            self.db.execute("""
                INSERT OR REPLACE INTO orderbook_data
                (exchange, symbol, timestamp, bids, asks, bid_ask_spread, mid_price)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (exchange, symbol, timestamp, bids_json, asks_json, 
                  bid_ask_spread, mid_price))
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Error storing order book: {e}")
            
    def _store_trade(
        self,
        exchange: str,
        symbol: str,
        trade_id: str,
        timestamp: int,
        side: str,
        price: float,
        amount: float,
        cost: float,
        taker_or_maker: Optional[str] = None,
        fee: Optional[float] = None,
        fee_currency: Optional[str] = None
    ):
        """
        Store individual trade in database.
        
        Args:
            exchange: Exchange name
            symbol: Trading pair
            trade_id: Unique trade identifier
            timestamp: Unix timestamp
            side: 'buy' or 'sell'
            price: Trade price
            amount: Trade amount
            cost: Total cost (price × amount)
            taker_or_maker: 'taker' or 'maker'
            fee: Trade fee amount
            fee_currency: Fee currency
        """
        try:
            self.db.execute("""
                INSERT OR IGNORE INTO trades_stream
                (exchange, symbol, trade_id, timestamp, side, price, amount, cost, 
                 taker_or_maker, fee, fee_currency)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (exchange, symbol, trade_id, timestamp, side, price, amount, cost,
                  taker_or_maker, fee, fee_currency))
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Error storing trade: {e}")
            
    async def start(self, enable_orderbook: bool = True, enable_trades: bool = False):
        """
        Start all websocket streams.
        
        Args:
            enable_orderbook: Whether to stream order book data (default: True)
            enable_trades: Whether to stream individual trades (default: False, high volume)
        """
        self.running = True
        await self.connect()
        
        # Create tasks for all subscriptions
        tasks = []
        
        for symbol in self.symbols:
            # Subscribe to OHLCV updates (1m by default)
            tasks.append(asyncio.create_task(self.watch_ohlcv(symbol, '1m')))
            
            # Subscribe to ticker updates
            tasks.append(asyncio.create_task(self.watch_ticker(symbol)))
            
            # Subscribe to order book updates
            if enable_orderbook:
                tasks.append(asyncio.create_task(self.watch_order_book(symbol)))
            
            # Subscribe to trade stream (optional - can be high volume)
            if enable_trades:
                tasks.append(asyncio.create_task(self.watch_trades(symbol)))
        
        # Run all tasks concurrently
        await asyncio.gather(*tasks)
        
    async def stop(self):
        """Stop all websocket streams."""
        self.running = False
        if self.exchange:
            await self.exchange.close()
        print(f"🛑 WebSocket disconnected from {self.exchange_name}")


# Usage Example
async def example_usage():
    """
    Example: Stream live data for BTC/USDT from Binance.
    
    This data goes into the same database tables as REST API data.
    """
    import sqlite3
    
    # Connect to database
    db_path = PROJECT_ROOT / "data" / "trading.db"
    conn = sqlite3.connect(str(db_path))
    
    # Initialize websocket manager
    ws_manager = WebSocketManager(
        exchange_name='binance',
        symbols=['BTC/USDT', 'ETH/USDT'],
        db_connection=conn,
        orderbook_depth=10
    )
    
    # Start streaming (runs forever)
    await ws_manager.start(enable_orderbook=True)


if __name__ == "__main__":
    # Run the websocket stream
    asyncio.run(example_usage())
