"""
WebSocket data streaming for live trading.

Uses CCXT Pro for websocket connections to exchanges.
Streams real-time data and stores in same database tables as REST API data.

Key Features:
- Real-time OHLCV updates (1m candles updated as they form)
- Real-time ticker/price updates (bid, ask, last)
- Order book updates (optional)
- Trade stream (optional)

Data Flow:
    Exchange WebSocket
        ↓
    CCXT Pro Handler
        ↓
    INSERT/UPDATE database
        ↓
    Same tables as REST data (ohlcv_data, ticker_data)

Note: WebSocket data and REST data are identical structure,
      just different delivery mechanisms (push vs pull).
"""

import asyncio
import ccxt.pro as ccxt
from typing import Dict, List, Optional
from pathlib import Path
import time

# Get project root (2 levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class WebSocketManager:
    """
    Manages websocket connections for real-time market data.
    
    Uses CCXT Pro (requires: pip install ccxt[pro])
    """
    
    def __init__(self, exchange_name: str, symbols: List[str], db_connection):
        """
        Initialize websocket manager.
        
        Args:
            exchange_name: Exchange to connect to (binance, coinbase, etc.)
            symbols: List of symbols to subscribe to
            db_connection: Database connection for storing data
        """
        self.exchange_name = exchange_name
        self.symbols = symbols
        self.db = db_connection
        self.exchange = None
        self.running = False
        
    async def connect(self):
        """Establish websocket connection to exchange."""
        exchange_class = getattr(ccxt, self.exchange_name)
        self.exchange = exchange_class({
            'enableRateLimit': True,
            # API keys loaded from environment if needed
        })
        print(f"✅ WebSocket connected to {self.exchange_name}")
        
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
                        timestamp=timestamp // 1000,  # Convert ms to seconds
                        open=open_price,
                        high=high,
                        low=low,
                        close=close,
                        volume=volume
                    )
                    
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
                
                # Store in database (same table as REST data!)
                self._store_ticker(
                    exchange=self.exchange_name,
                    symbol=symbol,
                    timestamp=int(time.time()),
                    bid=ticker.get('bid', 0),
                    ask=ticker.get('ask', 0),
                    last=ticker.get('last', 0),
                    volume_24h=ticker.get('quoteVolume', 0)
                )
                
            except Exception as e:
                print(f"❌ Error watching ticker {symbol}: {e}")
                await asyncio.sleep(5)
                
    async def watch_trades(self, symbol: str):
        """
        Stream individual trades (optional - for advanced strategies).
        
        Args:
            symbol: Trading pair (BTC/USDT)
        """
        print(f"💸 Watching trades: {symbol}")
        
        while self.running:
            try:
                trades = await self.exchange.watch_trades(symbol)
                
                # Process trades (can be used for advanced analysis)
                for trade in trades:
                    # Could store in a trades_stream table if needed
                    pass
                    
            except Exception as e:
                print(f"❌ Error watching trades {symbol}: {e}")
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
            print(f"❌ Error storing OHLCV: {e}")
            
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
            print(f"❌ Error storing ticker: {e}")
            
    async def start(self):
        """Start all websocket streams."""
        self.running = True
        await self.connect()
        
        # Create tasks for all subscriptions
        tasks = []
        
        for symbol in self.symbols:
            # Subscribe to OHLCV updates (1m by default)
            tasks.append(asyncio.create_task(self.watch_ohlcv(symbol, '1m')))
            
            # Subscribe to ticker updates
            tasks.append(asyncio.create_task(self.watch_ticker(symbol)))
        
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
        db_connection=conn
    )
    
    # Start streaming (runs forever)
    await ws_manager.start()


if __name__ == "__main__":
    # Run the websocket stream
    asyncio.run(example_usage())
