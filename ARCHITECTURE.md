# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         .env (Secrets)                          │
│  BINANCE_API_KEY, COINBASE_API_KEY, DATABASE_URL, LOG_LEVEL    │
└─────────────────────────────────────────────────────────────────┘
                              │ (shared)
                              ▼
        ┌─────────────────────────────────────────────┐
        │         Docker Compose Orchestration         │
        └─────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  Container 1  │     │  Container 2  │     │  Container N  │
│               │     │               │     │               │
│  BTC/USDT     │     │  ETH/USDT     │     │  SOL/USDT     │
│  Binance      │     │  Binance      │     │  Kraken       │
│  1h           │     │  15m          │     │  4h           │
│  RSI Strategy │     │  Scalping     │     │  Trend Follow │
└───────┬───────┘     └───────┬───────┘     └───────┬───────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │ (shared volumes)
                              ▼
        ┌─────────────────────────────────────────────┐
        │   Shared Volumes                            │
        │   • ./data/trading.db (SQLite database)     │
        │   • ./logs/ (Application logs)              │
        │   • ./config/strategies/ (Strategy configs) │
        └─────────────────────────────────────────────┘
```

## Container Architecture

Each container runs:

```
┌────────────────────────────────────────┐
│ Container: trader-btc-binance-1h       │
├────────────────────────────────────────┤
│                                        │
│  Entry: apps/trader/main.py            │
│         --config btc_binance_1h.yaml   │
│                                        │
│  Uses:                                 │
│   • packages/exchange/                 │
│   • packages/execution/                │
│   • packages/indicators/               │
│   • packages/database/                 │
│   • packages/risk/                     │
│   • packages/logging/                  │
│                                        │
│  Config: btc_binance_1h.yaml           │
│   - exchange: binance                  │
│   - symbol: BTC/USDT                   │
│   - timeframe: 1h                      │
│   - strategy: RSI + MACD               │
│                                        │
│  Resources:                            │
│   - CPU: 0.5 cores                     │
│   - Memory: 512MB                      │
│                                        │
└────────────────────────────────────────┘
```

## Data Flow

```
1. BACKFILLER (runs once or scheduled)
   ↓
   Fetches historical data from exchanges
   ↓
   Stores in ./data/trading.db
   ↓

2. BACKTESTER (testing phase)
   ↓
   Reads historical data from DB
   ↓
   Simulates strategy execution
   ↓
   Outputs performance metrics
   ↓

3. TRADER (production)
   ↓
   Reads config/strategies/*.yaml
   ↓
   Connects to exchange (via API keys in .env)
   ↓
   Fetches live market data
   ↓
   Calculates indicators (RSI, MACD, etc.)
   ↓
   Generates signals (buy/sell)
   ↓
   Executes trades (packages/execution/)
   ↓
   Logs to ./logs/
   ↓
   Stores trades in ./data/trading.db
```

## Configuration Separation

```
┌──────────────────────────────────────────────────────────────┐
│                    .env (SECRETS)                            │
│  • API Keys (BINANCE_API_KEY, etc.)                          │
│  • Database URL                                              │
│  • Log Level                                                 │
│  • System-wide settings                                      │
│                                                              │
│  🔒 One file, shared by all containers                       │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│           config/strategies/*.yaml (TRADING PARAMS)          │
│  • Exchange (binance, kraken, coinbase)                      │
│  • Symbol (BTC/USDT, ETH/USDT, SOL/USDT)                     │
│  • Timeframe (1m, 5m, 1h, 4h, 1d)                            │
│  • Strategy (RSI, MACD, indicators, signals)                 │
│  • Risk Management (position size, stop loss)                │
│                                                              │
│  📁 Multiple files, one per trading instance                 │
└──────────────────────────────────────────────────────────────┘
```

## Horizontal Scaling Example

```
Initial: 1 strategy
┌─────────────────┐
│ BTC/USDT 1h     │
│ Binance         │
└─────────────────┘

Scale: Add 2 more
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ BTC/USDT 1h     │  │ ETH/USDT 15m    │  │ SOL/USDT 4h     │
│ Binance         │  │ Binance         │  │ Kraken          │
└─────────────────┘  └─────────────────┘  └─────────────────┘

Scale: Add 3 more
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ BTC/USDT 1h     │  │ ETH/USDT 15m    │  │ SOL/USDT 4h     │
│ Binance         │  │ Binance         │  │ Kraken          │
└─────────────────┘  └─────────────────┘  └─────────────────┘
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ BTC/USD 1h      │  │ MATIC/USDT 30m  │  │ AVAX/USDT 2h    │
│ Coinbase        │  │ Binance         │  │ Bybit           │
└─────────────────┘  └─────────────────┘  └─────────────────┘

To add:
1. Create config/strategies/new_strategy.yaml
2. Add service to docker-compose.yml
3. Run: docker-compose up -d

NO CODE CHANGES NEEDED! 🎉
```

## Package Dependencies

```
apps/trader/main.py
    │
    ├─ packages/core/         → Core orchestration
    ├─ packages/exchange/     → CCXT wrapper
    ├─ packages/execution/    → Order placement
    ├─ packages/indicators/   → RSI, MACD, etc.
    ├─ packages/database/     → SQLite operations
    ├─ packages/risk/         → Position sizing, stop loss
    ├─ packages/logging/      → Structured logging
    └─ packages/timeframes/   → Timeframe utilities

All packages are reusable by:
- apps/trader/
- apps/backtester/
- apps/backfiller/
```

## Why This Works

✅ **Complete Modularity**: Zero hardcoded values  
✅ **Easy Scaling**: Add configs + docker-compose entries  
✅ **Isolated Instances**: Each container independent  
✅ **Shared Data**: All use same database  
✅ **Resource Control**: CPU/memory limits per instance  
✅ **Simple Deployment**: `docker-compose up -d`  
✅ **Easy Monitoring**: `docker-compose logs -f`  
✅ **Auto-Recovery**: Containers restart on failure
