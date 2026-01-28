"""
Migration script to normalize all timestamps in the database to milliseconds.
This fixes mixed timestamp formats (seconds vs milliseconds).
"""

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "data" / "trading.db"

def normalize_timestamp(ts: int) -> int:
    """Convert timestamp to milliseconds."""
    if ts < 100_000_000_000:  # Less than 10^11
        return ts * 1000
    return ts

def migrate():
    """Normalize all timestamps to milliseconds."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Special handling for ohlcv_data due to unique constraint
        print(f"🔄 Normalizing ohlcv_data.timestamp...")
        
        # Get all rows and check which need normalization
        cursor.execute("SELECT rowid, exchange, symbol, timeframe, timestamp FROM ohlcv_data ORDER BY timestamp")
        rows = cursor.fetchall()
        
        needs_normalization = []
        for rowid, exchange, symbol, timeframe, ts in rows:
            if ts < 100_000_000_000:  # Needs normalization
                normalized = normalize_timestamp(ts)
                needs_normalization.append((rowid, normalized, ts))
        
        if needs_normalization:
            # Disable constraints temporarily
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            # Delete old rows and re-insert with normalized timestamps
            deleted = 0
            for rowid, normalized, old_ts in needs_normalization:
                cursor.execute("DELETE FROM ohlcv_data WHERE rowid = ?", (rowid,))
                deleted += cursor.rowcount
            
            # Re-create rows with normalized timestamps
            # We need to re-fetch because we deleted them
            cursor.execute("SELECT rowid, exchange, symbol, timeframe, timestamp FROM ohlcv_data ORDER BY timestamp")
            updated = 0
            
            # Actually, let's do this more carefully with a temporary table
            print("   Creating temporary table...")
            cursor.execute("""
                CREATE TEMPORARY TABLE ohlcv_temp AS 
                SELECT exchange, symbol, timeframe, 
                       CASE 
                           WHEN timestamp < 100000000000 THEN timestamp * 1000
                           ELSE timestamp
                       END as timestamp,
                       open, high, low, close, volume
                FROM ohlcv_data
            """)
            
            cursor.execute("DELETE FROM ohlcv_data")
            cursor.execute("""
                INSERT INTO ohlcv_data (exchange, symbol, timeframe, timestamp, open, high, low, close, volume)
                SELECT exchange, symbol, timeframe, timestamp, open, high, low, close, volume
                FROM ohlcv_temp
            """)
            
            cursor.execute("DROP TABLE ohlcv_temp")
            cursor.execute("PRAGMA foreign_keys = ON")
            
            print(f"   ✅ Normalized ohlcv_data")
        else:
            print(f"   ✅ Already normalized")
        
        # Get all tables with timestamp columns
        tables_to_migrate = {
            'ticker_data': ['timestamp'],
            'trades': ['entry_time', 'exit_time'],
            'signals': ['timestamp'],
            'indicator_cache': ['timestamp'],
            'unfillable_gaps': ['gap_start', 'gap_end'],
        }
        
        for table, columns in tables_to_migrate.items():
            # Check if table exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cursor.fetchone():
                print(f"⏭️  Table {table} doesn't exist, skipping...")
                continue
            
            for column in columns:
                # Check if column exists
                cursor.execute(f"PRAGMA table_info({table})")
                columns_info = [col[1] for col in cursor.fetchall()]
                if column not in columns_info:
                    print(f"⏭️  Column {table}.{column} doesn't exist, skipping...")
                    continue
                
                print(f"🔄 Normalizing {table}.{column}...")
                
                # Get all unique values to normalize
                cursor.execute(f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL")
                timestamps = [row[0] for row in cursor.fetchall()]
                
                if not timestamps:
                    print(f"   No data to migrate")
                    continue
                
                # Check if already normalized (all >= 10^11)
                if all(ts >= 100_000_000_000 for ts in timestamps):
                    print(f"   ✅ Already normalized")
                    continue
                
                # Normalize timestamps in-place
                updated_count = 0
                for ts in timestamps:
                    normalized = normalize_timestamp(ts)
                    if normalized != ts:
                        cursor.execute(f"UPDATE {table} SET {column} = ? WHERE {column} = ?", (normalized, ts))
                        updated_count += cursor.rowcount
                
                print(f"   ✅ Updated {updated_count} rows")
        
        conn.commit()
        print("\n✅ Migration complete!")
        
    except sqlite3.Error as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
