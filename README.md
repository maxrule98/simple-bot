# Trading Bot - Modular Architecture

A cryptocurrency trading bot with a modular, extensible architecture. Scans multiple trading pairs using CCXT, stores data in SQLite, and generates trading signals based on configurable strategies.

## Features

- 📊 **Multi-pair monitoring** - Scan multiple trading pairs simultaneously
- 💾 **SQLite database** - Persistent storage for price history and signals
- 📈 **Pluggable strategies** - Easy-to-extend strategy framework
- 🔄 **CCXT integration** - Access to 100+ cryptocurrency exchanges
- ⚡ **UV package management** - Fast dependency management
- 🧩 **Modular design** - Clean separation of concerns

## Project Structure

```
simple-bot/
├── main.py           # Entry point - orchestrates the bot
├── config.py         # Configuration management
├── database.py       # Database operations
├── exchange.py       # Exchange interactions (CCXT)
├── scanner.py        # Market scanning logic
├── strategy.py       # Trading strategies
├── data/             # SQLite database (auto-created)
│   └── trading.db
├── pyproject.toml    # Project dependencies
└── README.md         # This file
```

## Architecture

### Core Modules

#### `config.py`

Centralized configuration using dataclasses:

- `ExchangeConfig` - Exchange settings (name, API keys, rate limits)
- `DatabaseConfig` - Database path configuration
- `TradingConfig` - Trading pairs, thresholds, strategy parameters
- `BotConfig` - Main configuration container

#### `database.py`

Database operations:

- Connection management
- Table initialization (pairs, prices, signals)
- CRUD operations for market data and signals
- Query helpers for strategy analysis

#### `exchange.py`

Exchange interactions via CCXT:

- Multi-exchange support
- Ticker data fetching
- OHLCV data retrieval
- Market discovery
- Rate limiting

#### `strategy.py`

Trading strategy framework:

- `Strategy` - Base strategy class
- `PriceChangeStrategy` - Momentum-based signals
- `VolumeStrategy` - Volume spike detection
- `MultiStrategy` - Combine multiple strategies

#### `scanner.py`

Main orchestration:

- Coordinates all modules
- Manages scan lifecycle
- Data collection and storage
- Signal generation and display

## Quick Start

### Installation

```bash
uv sync
```

### Run the Bot

```bash
uv run python main.py
```

### Expected Output

```
============================================================
Trading Bot - Market Scanner
============================================================

✓ Database initialized
✓ Connected to Binance

Monitoring 5 pairs:

✓ BTC/USDT: $87831.53
✓ ETH/USDT: $2884.45
...

✓ Fetched data for 5 pairs
✓ Data saved to database

Analyzing market data...
  → Signal: BUY ETH/USDT @ $2884.45 - Change: +1.23%

Recent signals (3):
  [BUY] ETH/USDT @ $2884.45 - Change: +1.23% (2026-01-25 10:30:00)
```

## Configuration

### Basic Configuration

Edit `main.py` to customize settings:

```python
config = BotConfig(
    exchange=ExchangeConfig(
        name="binance",  # or "kraken", "coinbase", etc.
        enable_rate_limit=True,
        market_type="spot"
    ),
    trading=TradingConfig(
        pairs=['BTC/USDT', 'ETH/USDT', 'SOL/USDT'],
        price_change_threshold=1.0
    )
)
```

### Add API Keys (Optional)

For private endpoints or trading:

```python
config = BotConfig(
    exchange=ExchangeConfig(
        name="binance",
        api_key="YOUR_API_KEY",
        secret="YOUR_SECRET"
    )
)
```

### Dynamic Pair Discovery

Let the bot discover pairs automatically:

```python
config = BotConfig(
    trading=TradingConfig(
        pairs=[],  # Empty list triggers auto-discovery
        quote_currency="USDT",
        max_pairs=20  # Scan top 20 USDT pairs
    )
)
```

## Custom Strategies

### Create a New Strategy

```python
from strategy import Strategy

class MyStrategy(Strategy):
    def __init__(self, db, my_param=10):
        super().__init__(db, name="my_strategy")
        self.my_param = my_param

    def analyze(self, symbol, ticker_data):
        # Your logic here
        # Return signal dict or None

        return {
            'symbol': symbol,
            'signal_type': 'BUY',
            'price': ticker_data['close'],
            'strategy': self.name,
            'metadata': 'My reason'
        }
```

### Use Multiple Strategies

```python
from strategy import MultiStrategy, PriceChangeStrategy, VolumeStrategy

strategies = [
    PriceChangeStrategy(scanner.db, threshold=1.0),
    VolumeStrategy(scanner.db, volume_threshold=1.5)
]

multi = MultiStrategy(strategies)
scanner.set_strategy(multi)
```

### Built-in Strategies

#### PriceChangeStrategy

Generates signals based on price momentum:

- **BUY** when price increases > threshold%
- **SELL** when price decreases > threshold%

```python
strategy = PriceChangeStrategy(db, threshold=1.5)
```

#### VolumeStrategy

Detects volume spikes (placeholder - extend as needed):

```python
strategy = VolumeStrategy(db, volume_threshold=2.0)
```

## Extending the Bot

### Add a New Exchange

```python
config = BotConfig(
    exchange=ExchangeConfig(
        name="kraken",  # or any CCXT-supported exchange
        enable_rate_limit=True
    )
)
```

### Add Technical Indicators

```bash
uv add pandas ta-lib pandas-ta
```

Then in your strategy:

```python
import pandas as pd
from strategy import Strategy

class RSIStrategy(Strategy):
    def analyze(self, symbol, ticker_data):
        # Fetch OHLCV data
        # Calculate RSI
        # Generate signals
        pass
```

### Scheduled Scanning

For continuous monitoring, use a scheduler:

```bash
uv add schedule
```

```python
import schedule
import time

def job():
    scanner = MarketScanner(config)
    scanner.initialize()
    scanner.set_strategy(strategy)
    scanner.scan()
    scanner.cleanup()

schedule.every(5).minutes.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)
```

## Database Schema

### prices

- `symbol` - Trading pair (e.g., BTC/USDT)
- `timestamp` - Data timestamp
- `open, high, low, close, volume` - OHLCV data
- `created_at` - Record creation time

### signals

- `symbol` - Trading pair
- `signal_type` - BUY/SELL
- `price` - Price at signal
- `strategy` - Strategy name
- `metadata` - Additional info
- `timestamp` - Signal generation time

## Adding Dependencies

```bash
uv add pandas          # Data analysis
uv add pandas-ta       # Technical indicators
uv add python-dotenv   # Environment variables
uv add schedule        # Task scheduling
uv add requests        # Additional API calls
```

## Environment Variables

Create `.env` file:

```bash
EXCHANGE_API_KEY=your_api_key
EXCHANGE_SECRET=your_secret
QUOTE_CURRENCY=USDT
PRICE_THRESHOLD=1.5
```

Load in config:

```bash
uv add python-dotenv
```

```python
from dotenv import load_dotenv
import os

load_dotenv()

config = BotConfig(
    exchange=ExchangeConfig(
        api_key=os.getenv('EXCHANGE_API_KEY', ''),
        secret=os.getenv('EXCHANGE_SECRET', '')
    )
)
```

## Safety & Best Practices

⚠️ **Important Safety Guidelines:**

- **Paper trading first** - Test thoroughly before using real funds
- **Start small** - Use minimal amounts when going live
- **Risk management** - Implement stop-losses and position sizing
- **Monitor actively** - Don't leave bots unattended
- **API security** - Never commit API keys, use environment variables
- **Rate limits** - Always enable rate limiting to avoid bans
- **Error handling** - Implement comprehensive error handling
- **Logging** - Add detailed logging for debugging

## Development

### Run Tests (when implemented)

```bash
uv run pytest
```

### Code Style

```bash
uv add black ruff
uv run black .
uv run ruff check .
```

### Type Checking

```bash
uv add mypy
uv run mypy *.py
```

## Troubleshooting

### "No signals generated yet"

- Run the bot multiple times to build price history
- Signals need at least 2 data points to detect changes
- Lower the `price_change_threshold` for more sensitive detection

### Exchange Connection Errors

- Check your internet connection
- Verify exchange name is correct
- Some exchanges require API keys even for market data
- Enable rate limiting to avoid bans

### Database Errors

- Ensure `data/` directory is writable
- Check disk space
- Database file: `data/trading.db`

## License

MIT

## Disclaimer

This software is for educational purposes only. Cryptocurrency trading carries significant risk. Never invest more than you can afford to lose. The developers are not responsible for any financial losses incurred through the use of this software.
