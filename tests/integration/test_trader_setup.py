"""Quick test script to validate trader setup."""

import sys
from pathlib import Path

print("=" * 60)
print("Trader Setup Validation")
print("=" * 60)

# Check required files
required_files = [
    "packages/signals/types.py",
    "packages/execution/manager.py",
    "packages/strategies/base.py",
    "packages/strategies/loader.py",
    "packages/strategies/conventional/rsi_mean_reversion.py",
    "apps/trader/runtime.py",
    "config/strategies/btc_rsi_strategy.yaml",
]

print("\n✓ Checking required files...")
all_exist = True
for file_path in required_files:
    path = Path(file_path)
    status = "✓" if path.exists() else "✗ MISSING"
    print(f"  {status} {file_path}")
    if not path.exists():
        all_exist = False

if not all_exist:
    print("\n✗ Some files are missing!")
    sys.exit(1)

# Check imports
print("\n✓ Checking imports...")
try:
    from packages.signals.types import Signal, SignalType, SignalSource
    print("  ✓ packages.signals.types")
except ImportError as e:
    print(f"  ✗ packages.signals.types: {e}")
    sys.exit(1)

try:
    from packages.execution.manager import ExecutionManager
    print("  ✓ packages.execution.manager")
except ImportError as e:
    print(f"  ✗ packages.execution.manager: {e}")
    sys.exit(1)

try:
    from packages.strategies.base import BaseStrategy
    print("  ✓ packages.strategies.base")
except ImportError as e:
    print(f"  ✗ packages.strategies.base: {e}")
    sys.exit(1)

try:
    from packages.strategies.loader import StrategyLoader
    print("  ✓ packages.strategies.loader")
except ImportError as e:
    print(f"  ✗ packages.strategies.loader: {e}")
    sys.exit(1)

try:
    from packages.strategies.conventional.rsi_mean_reversion import RSIMeanReversion
    print("  ✓ packages.strategies.conventional.rsi_mean_reversion")
except ImportError as e:
    print(f"  ✗ packages.strategies.conventional.rsi_mean_reversion: {e}")
    sys.exit(1)

# Check config loading
print("\n✓ Checking config loading...")
try:
    config = StrategyLoader.load_config("config/strategies/btc_rsi_strategy.yaml")
    print(f"  ✓ Config loaded: {config['strategy']['name']}")
    print(f"    - Exchange: {config['market']['exchange']}")
    print(f"    - Symbol: {config['market']['symbol']}")
    print(f"    - Timeframe: {config['market']['primary_timeframe']}")
except Exception as e:
    print(f"  ✗ Config loading failed: {e}")
    sys.exit(1)

# Check database
print("\n✓ Checking database...")
try:
    from packages.database.db import DatabaseManager
    db = DatabaseManager("data/trading.db")
    
    # Check if tables exist
    tables = db.query("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = [t[0] for t in tables]
    
    required_tables = ["ohlcv_data", "trades", "signals", "positions"]
    missing_tables = [t for t in required_tables if t not in table_names]
    
    if missing_tables:
        print(f"  ⚠ Missing tables: {missing_tables}")
        print(f"  Run: python schema.py")
    else:
        print(f"  ✓ All required tables exist")
    
    # Check if we have some data
    ohlcv_count = db.query("SELECT COUNT(*) FROM ohlcv_data")[0][0]
    print(f"  ✓ OHLCV records: {ohlcv_count:,}")
    
    if ohlcv_count < 100:
        print(f"  ⚠ Limited data available - run backfiller for better results")
    
    db.close()
except Exception as e:
    print(f"  ✗ Database check failed: {e}")
    sys.exit(1)

# Check environment variables
print("\n✓ Checking environment variables...")
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("MEXC_API_KEY")
api_secret = os.getenv("MEXC_API_SECRET")

if api_key and api_secret:
    print(f"  ✓ MEXC_API_KEY: {api_key[:8]}...")
    print(f"  ✓ MEXC_API_SECRET: {'*' * 8}...")
else:
    print(f"  ⚠ API credentials not set (required for trading)")
    print(f"  Set in .env: MEXC_API_KEY and MEXC_API_SECRET")

print("\n" + "=" * 60)
print("✓ Setup validation complete!")
print("=" * 60)

print("\nNext steps:")
print("  1. Paper trade test:")
print("     uv run python -m apps.trader.main --config config/strategies/btc_rsi_strategy.yaml --mode paper")
print()
print("  2. Monitor logs:")
print("     tail -f logs/trader.log")
print()
print("  3. Check database:")
print("     sqlite3 data/trading.db 'SELECT * FROM trades ORDER BY timestamp DESC LIMIT 5;'")
