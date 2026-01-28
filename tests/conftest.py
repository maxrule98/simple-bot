"""
Test fixtures and configuration for pytest.

Provides shared fixtures, mocks, and test utilities across all tests.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import sqlite3
from unittest.mock import Mock, MagicMock
from typing import Dict, List


@pytest.fixture(scope="session")
def project_root():
    """Get project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def test_data_dir(project_root):
    """Get test data directory."""
    return project_root / "tests" / "fixtures" / "data"


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    # Initialize schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create minimal schema for testing
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv_data (
            exchange TEXT NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            PRIMARY KEY (exchange, symbol, timeframe, timestamp)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id TEXT NOT NULL,
            exchange TEXT NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            price REAL NOT NULL,
            quantity REAL NOT NULL,
            timestamp INTEGER NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='1min')
    
    # Generate realistic price data
    base_price = 100.0
    prices = []
    for i in range(100):
        # Random walk with drift
        change = np.random.randn() * 0.5
        base_price += change
        prices.append(base_price)
    
    df = pd.DataFrame({
        'timestamp': [int(d.timestamp() * 1000) for d in dates],
        'open': prices,
        'high': [p + abs(np.random.randn()) for p in prices],
        'low': [p - abs(np.random.randn()) for p in prices],
        'close': [p + np.random.randn() * 0.2 for p in prices],
        'volume': np.random.uniform(1000, 10000, 100)
    })
    
    # Ensure high >= close, open, low and low <= all
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    return df


@pytest.fixture
def sample_price_series():
    """Generate simple price DataFrame for indicator testing."""
    # Indicators expect DataFrame with 'close' column
    np.random.seed(42)  # For reproducibility
    prices = [100 + i + np.random.randn() for i in range(50)]
    return pd.DataFrame({'close': prices})


@pytest.fixture
def mock_exchange():
    """Create mock CCXT exchange."""
    mock = MagicMock()
    mock.id = 'mexc'
    mock.name = 'MEXC'
    mock.has = {
        'fetchTicker': True,
        'fetchOHLCV': True,
        'createOrder': True,
        'fetchBalance': True,
    }
    mock.markets = {
        'BTC/USDT': {
            'id': 'BTCUSDT',
            'symbol': 'BTC/USDT',
            'base': 'BTC',
            'quote': 'USDT',
            'active': True,
            'limits': {
                'amount': {'min': 0.001, 'max': 10000},
                'price': {'min': 0.01, 'max': 1000000},
            }
        }
    }
    
    # Mock methods
    mock.fetch_ticker.return_value = {
        'symbol': 'BTC/USDT',
        'bid': 89000.0,
        'ask': 89001.0,
        'last': 89000.5,
        'timestamp': int(datetime.now().timestamp() * 1000)
    }
    
    mock.fetch_ohlcv.return_value = [
        [int((datetime.now() - timedelta(minutes=i)).timestamp() * 1000),
         89000 + i, 89100 + i, 88900 + i, 89050 + i, 100.0]
        for i in range(10)
    ]
    
    mock.create_order.return_value = {
        'id': 'order_123',
        'symbol': 'BTC/USDT',
        'type': 'market',
        'side': 'buy',
        'price': 89000.0,
        'amount': 0.001,
        'status': 'closed',
        'timestamp': int(datetime.now().timestamp() * 1000)
    }
    
    mock.fetch_balance.return_value = {
        'USDT': {'free': 10000.0, 'used': 0.0, 'total': 10000.0},
        'BTC': {'free': 0.1, 'used': 0.0, 'total': 0.1}
    }
    
    return mock


@pytest.fixture
def sample_strategy_config():
    """Sample strategy configuration for testing."""
    return {
        'strategy': {
            'name': 'Test Strategy',
            'exchange': 'mexc',
            'symbol': 'BTC/USDT',
            'timeframe': '1m',
            'strategy_id': 'test-strategy-001'
        },
        'indicators': [
            {'name': 'RSI', 'params': {'period': 14}}
        ],
        'entry': {
            'conditions': ['RSI < 30']
        },
        'exit': {
            'conditions': ['RSI > 70']
        },
        'risk': {
            'position_size': 0.001,
            'stop_loss_pct': 2.0,
            'take_profit_pct': 4.0
        }
    }


@pytest.fixture
def sample_candle_data():
    """Sample candle data for validation testing."""
    return {
        'timestamp': int(datetime.now().timestamp() * 1000),
        'open': 100.0,
        'high': 105.0,
        'low': 95.0,
        'close': 102.0,
        'volume': 1000.0
    }


@pytest.fixture
def invalid_candle_data():
    """Invalid candle data for testing validation."""
    return {
        'timestamp': int(datetime.now().timestamp() * 1000),
        'open': 100.0,
        'high': 95.0,  # Invalid: high < low
        'low': 105.0,
        'close': 102.0,
        'volume': -100.0  # Invalid: negative volume
    }


# Parametrized fixtures for timeframes
@pytest.fixture(params=['1m', '5m', '15m', '1h', '4h', '1d'])
def timeframe(request):
    """Parametrized timeframe fixture."""
    return request.param


# Parametrized fixtures for exchanges
@pytest.fixture(params=['mexc', 'binance', 'coinbase'])
def exchange_name(request):
    """Parametrized exchange name fixture."""
    return request.param


# Parametrized fixtures for symbols
@pytest.fixture(params=['BTC/USDT', 'ETH/USDT', 'SOL/USDT'])
def trading_symbol(request):
    """Parametrized trading symbol fixture."""
    return request.param


@pytest.fixture
def sample_trade():
    """Sample trade data."""
    return {
        'strategy_id': 'test-001',
        'exchange': 'mexc',
        'symbol': 'BTC/USDT',
        'side': 'buy',
        'price': 89000.0,
        'quantity': 0.001,
        'timestamp': int(datetime.now().timestamp() * 1000),
        'order_id': 'order_123'
    }


@pytest.fixture
def sample_position():
    """Sample position data."""
    return {
        'strategy_id': 'test-001',
        'symbol': 'BTC/USDT',
        'side': 'long',
        'entry_price': 89000.0,
        'quantity': 0.001,
        'stop_loss': 87000.0,
        'take_profit': 93000.0,
        'unrealized_pnl': 50.0
    }


# Helper functions
def generate_ohlcv_batch(count: int = 100, exchange: str = 'mexc', 
                         symbol: str = 'BTC/USDT', timeframe: str = '1m') -> List[Dict]:
    """Generate batch of OHLCV records."""
    base_time = int(datetime.now().timestamp() * 1000)
    tf_ms = 60000  # 1m in milliseconds
    
    batch = []
    price = 89000.0
    
    for i in range(count):
        price += np.random.randn() * 10
        batch.append({
            'exchange': exchange,
            'symbol': symbol,
            'timeframe': timeframe,
            'timestamp': base_time - (i * tf_ms),
            'open': price,
            'high': price + abs(np.random.randn() * 5),
            'low': price - abs(np.random.randn() * 5),
            'close': price + np.random.randn() * 2,
            'volume': np.random.uniform(100, 1000)
        })
    
    return batch


# Mark fixtures that can be shared
pytest.fixture(generate_ohlcv_batch)
