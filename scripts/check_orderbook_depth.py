"""
Check order book depth from latest snapshot.

Shows how many bid and ask levels were captured in the most recent order book snapshot.
"""

import json
import sqlite3
from pathlib import Path


def main():
    """Query and display orderbook depth from latest snapshot."""
    
    # Connect to database
    db_path = Path(__file__).resolve().parent.parent / "data" / "trading.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get latest orderbook snapshot
    cursor.execute("""
        SELECT exchange, symbol, timestamp, bids, asks, bid_ask_spread, mid_price
        FROM orderbook_data
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    
    if not result:
        print("❌ No orderbook data found in database")
        conn.close()
        return
    
    exchange, symbol, timestamp, bids_json, asks_json, spread, mid_price = result
    
    # Parse JSON
    bids = json.loads(bids_json)
    asks = json.loads(asks_json)
    
    # Count levels
    num_bids = len(bids)
    num_asks = len(asks)
    
    # Display results
    print("=" * 80)
    print("📚 Latest Order Book Snapshot Analysis")
    print("=" * 80)
    print()
    print(f"Exchange:  {exchange}")
    print(f"Symbol:    {symbol}")
    print(f"Timestamp: {timestamp}")
    print(f"Mid Price: ${mid_price:,.2f}")
    print(f"Spread:    ${spread:.4f}")
    print()
    print("=" * 80)
    print("📊 Depth Analysis")
    print("=" * 80)
    print(f"🟢 Bid Levels:  {num_bids}")
    print(f"🔴 Ask Levels:  {num_asks}")
    print(f"📈 Total Levels: {num_bids + num_asks}")
    print()
    
    # Show top 3 bids and asks
    print("Top 3 Bids:")
    for i, (price, amount) in enumerate(bids[:3], 1):
        print(f"   {i}. ${price:,.2f} × {amount:.4f} = ${price * amount:,.2f}")
    
    print()
    print("Top 3 Asks:")
    for i, (price, amount) in enumerate(asks[:3], 1):
        print(f"   {i}. ${price:,.2f} × {amount:.4f} = ${price * amount:,.2f}")
    
    print()
    
    # Calculate total liquidity
    bid_liquidity = sum(price * amount for price, amount in bids)
    ask_liquidity = sum(price * amount for price, amount in asks)
    
    print("=" * 80)
    print("💰 Liquidity Analysis")
    print("=" * 80)
    print(f"Bid Side Liquidity: ${bid_liquidity:,.2f}")
    print(f"Ask Side Liquidity: ${ask_liquidity:,.2f}")
    print(f"Total Liquidity:    ${bid_liquidity + ask_liquidity:,.2f}")
    print()
    
    conn.close()


if __name__ == "__main__":
    main()
