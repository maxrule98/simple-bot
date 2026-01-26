"""
Test WebSocket streaming with order book and trade support.

This script demonstrates real-time data collection:
- OHLCV (1m candles forming in real-time)
- Ticker (bid/ask/last price updates)
- Order Book (top 10 bid/ask levels with liquidity)
- Trade Stream (individual trades for order flow)

Run for ~30 seconds to see data flowing into database.
"""

import asyncio
import sqlite3
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from packages.websocket.websocket import WebSocketManager


async def main():
    """Run websocket test with order book and trade streaming."""
    
    print("=" * 80)
    print("🔴 LIVE WebSocket Test - Full Market Data Streaming")
    print("=" * 80)
    print()
    
    # Configuration
    exchange = 'mexc'
    symbols = ['BTC/USDT']  # Start with one symbol for testing
    test_duration = 30  # seconds
    
    print(f"📊 Configuration:")
    print(f"   Exchange: {exchange}")
    print(f"   Symbols: {', '.join(symbols)}")
    print(f"   Duration: {test_duration} seconds")
    print(f"   Order Book Depth: 10 levels")
    print()
    
    # Connect to database
    db_path = PROJECT_ROOT / "data" / "trading.db"
    conn = sqlite3.connect(str(db_path))
    
    # Initialize WebSocket manager
    ws_manager = WebSocketManager(
        exchange_name=exchange,
        symbols=symbols,
        db_connection=conn,
        orderbook_depth=10
    )
    
    print("🚀 Starting WebSocket streams...")
    print("   📊 OHLCV (1m candles)")
    print("   💹 Ticker (price updates)")
    print("   📚 Order Book (depth)")
    print("   💸 Trade Stream (individual trades)")
    print()
    print("⏱️  Running for 30 seconds... (Ctrl+C to stop early)")
    print("=" * 80)
    print()
    
    # Run for specified duration
    try:
        await asyncio.wait_for(
            ws_manager.start(enable_orderbook=True, enable_trades=True), 
            timeout=test_duration
        )
    except asyncio.TimeoutError:
        pass
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    finally:
        await ws_manager.stop()
    
    print()
    print("=" * 80)
    print("📈 Data Collection Summary")
    print("=" * 80)
    
    # Query collected data
    cursor = conn.cursor()
    
    # OHLCV count
    cursor.execute("""
        SELECT COUNT(*) FROM ohlcv_data 
        WHERE exchange = ? AND symbol = ? 
        AND timestamp > strftime('%s', 'now') - 60
    """, (exchange, symbols[0]))
    ohlcv_count = cursor.fetchone()[0]
    
    # Ticker count
    cursor.execute("""
        SELECT COUNT(*) FROM ticker_data 
        WHERE exchange = ? AND symbol = ?
        AND timestamp > strftime('%s', 'now') - 60
    """, (exchange, symbols[0]))
    ticker_count = cursor.fetchone()[0]
    
    # Order book count
    cursor.execute("""
        SELECT COUNT(*) FROM orderbook_data 
        WHERE exchange = ? AND symbol = ?
        AND timestamp > strftime('%s', 'now') - 60
    """, (exchange, symbols[0]))
    orderbook_count = cursor.fetchone()[0]
    
    # Trades count
    cursor.execute("""
        SELECT COUNT(*) FROM trades_stream 
        WHERE exchange = ? AND symbol = ?
        AND timestamp > strftime('%s', 'now') - 60
    """, (exchange, symbols[0]))
    trades_count = cursor.fetchone()[0]
    
    print(f"📊 OHLCV Updates:        {ohlcv_count}")
    print(f"💹 Ticker Updates:       {ticker_count}")
    print(f"📚 Order Book Snapshots: {orderbook_count}")
    print(f"💸 Individual Trades:    {trades_count}")
    print()
    
    # Show latest order book
    cursor.execute("""
        SELECT timestamp, bids, asks, bid_ask_spread, mid_price
        FROM orderbook_data
        WHERE exchange = ? AND symbol = ?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (exchange, symbols[0]))
    
    latest_ob = cursor.fetchone()
    if latest_ob:
        import json
        timestamp, bids_json, asks_json, spread, mid = latest_ob
        bids = json.loads(bids_json)
        asks = json.loads(asks_json)
        
        print(f"📚 Latest Order Book Snapshot:")
        print(f"   Time: {timestamp}")
        print(f"   Mid Price: ${mid:.2f}")
        print(f"   Spread: ${spread:.4f}")
        print()
        print(f"   Top 5 Bids:")
        for i, (price, amount) in enumerate(bids[:5], 1):
            print(f"      {i}. ${price:,.2f} × {amount:.4f}")
        print()
        print(f"   Top 5 Asks:")
        for i, (price, amount) in enumerate(asks[:5], 1):
            print(f"      {i}. ${price:,.2f} × {amount:.4f}")
    
    # Show recent trades
    cursor.execute("""
        SELECT timestamp, side, price, amount, cost
        FROM trades_stream
        WHERE exchange = ? AND symbol = ?
        ORDER BY timestamp DESC
        LIMIT 10
    """, (exchange, symbols[0]))
    
    recent_trades = cursor.fetchall()
    if recent_trades:
        print()
        print(f"💸 Recent Trades (Last 10):")
        for ts, side, price, amount, cost in recent_trades:
            side_emoji = "🟢" if side == 'buy' else "🔴"
            print(f"   {side_emoji} {side.upper():4s} ${price:,.2f} × {amount:.4f} = ${cost:,.2f}")
    
    conn.close()
    print()
    print("✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(main())
