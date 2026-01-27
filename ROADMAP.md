# Project Roadmap

This document centralizes the implementation plan and timeline for the Simple Trading Bot project. It is a condensed, actionable version of the design in `docs/TRADER_ARCHITECTURE.md` and the README.

## Goals

- Keep the system fully dynamic (no hardcoding)
- Modular architecture: data, strategy, execution, ML, monitoring
- Support three runtime modes: `live`, `paper`, `backtest`
- Enable ML-first workflows with rolling-window training
- Provide institutional-grade indicators (True VWAP) and monitoring

## High-Level Phases (9-week plan)

Phase 1 — Core Trading Runtime (Weeks 1-2)

- Implement execution manager: `packages/execution/manager.py`
- Implement base strategy: `packages/strategies/base.py`
- Implement strategy loader: `packages/strategies/loader.py`
- Implement trading runtime: `apps/trader/runtime.py`
- Deliverable: Paper-trade RSI strategy on 1m BTC/USDT

Phase 2 — Signal Framework (Week 3)

- Build `packages/signals/` (types, generators, aggregator)
- Implement technical signal generator
- Implement aggregator modes (voting/weighted/unanimous)
- Implement exit manager (tiered TP / trailing / time-based)
- Deliverable: Multi-timeframe strategy with tiered exits

Phase 3 — Indicators & True VWAP (Week 4)

- Implement conventional indicators (RSI, MACD, BB)
- Implement True VWAP from trades stream (`packages/indicators/.../vwap_true`)
- Deliverable: VWAP mean reversion strategy in paper mode

# Project Roadmap

This document centralizes the implementation plan and timeline for the Simple Trading Bot project. It is a condensed, actionable version of the design in `docs/TRADER_ARCHITECTURE.md` and the README.

## Goals

- Keep the system fully dynamic (no hardcoding)
- Modular architecture: data, strategy, execution, ML, monitoring
- Support three runtime modes: `live`, `paper`, `backtest`
- Enable ML-first workflows with rolling-window training
- Provide institutional-grade indicators (True VWAP) and monitoring

## High-Level Phases (9-week plan)

Phase 1 — Core Trading Runtime (Weeks 1-2)

- Implement execution manager: `packages/execution/manager.py`
- Implement base strategy: `packages/strategies/base.py`
- Implement strategy loader: `packages/strategies/loader.py`
- Implement trading runtime: `apps/trader/runtime.py`
- Deliverable: Paper-trade RSI strategy on 1m BTC/USDT

Phase 2 — Signal Framework (Week 3)

- Build `packages/signals/` (types, generators, aggregator)
- Implement technical signal generator
- Implement aggregator modes (voting/weighted/unanimous)
- Implement exit manager (tiered TP / trailing / time-based)
- Deliverable: Multi-timeframe strategy with tiered exits

Phase 3 — Indicators & True VWAP (Week 4)

- Implement conventional indicators (RSI, MACD, BB)
- Implement True VWAP from trades stream (`packages/indicators/.../vwap_true`)
- Deliverable: VWAP mean reversion strategy in paper mode

Phase 4 — ML Integration (Weeks 5-6)

- Implement `packages/ml/`:
  - `data_loader.py` (rolling window)
  - `feature_engineering.py` (indicators + VWAP + lags)
  - model modules (LSTM / RF / XGBoost)
  - evaluation & deployment utilities
- Implement ML signal generator and integrate with strategies
- Deliverable: Daily retraining and ML-enhanced strategy

Phase 5 — Monitoring & Visualization (Week 7)

- Add Prometheus metrics support (`packages/prometheus/metrics.py`)
- Compose Grafana + Prometheus + Pushgateway
- Create Grafana dashboard JSON (live + historical unified chart, depth chart)
- Deliverable: Real-time dashboard with sub-second updates

Phase 6 — Backtester & Validation (Week 8)

- Implement `apps/backtester/main.py` (replay historical candles using same strategy code)
- Add configurable simulated execution/slippage
- Deliverable: Backtest reports for all strategies

Phase 7 — Production Deployment (Week 9+)

- Docker multi-instance deployment (one container per strategy)
- Start with paper for 1–2 weeks, then live small-cap deployment
- Monitoring + alerting + model rollback policies

## Priorities (short list)

1. Core execution & strategy loader (critical)
2. Signal framework and multi-timeframe support
3. True VWAP + indicators
4. ML pipeline and continuous retraining
5. Prometheus/Grafana integration
6. Backtester and validation

## Strategy & ML Principles

- Strategy code is identical across live/paper/backtest
- Execution layer controls sandbox/live switching (`set_sandbox_mode`)
- Strategies are YAML-configured, dynamically loaded Python classes
- Signals are rich objects (type, source, confidence, metadata)
- ML training uses unified DB (historical + live trades) as a rolling window
- True VWAP is computed from `trades_data` (not OHLCV approximations)

## Short-Term Next Steps (this sprint)

- Implement `packages/execution/manager.py` (skeleton + tests)
- Implement `packages/strategies/base.py` and `loader.py`
- Wire a minimal `apps/trader/runtime.py` to run in `paper` mode
- Add basic Prometheus metric hooks (price, trades, strategy signal)

## How to use this file

- This is the canonical implementation plan; keep it lightweight and actionable.
- For design details and examples, see `docs/TRADER_ARCHITECTURE.md` and `docs/GRAFANA_PROMETHEUS.md`.
- Update this file as milestones complete or priorities change.

---

_Last updated: 2026-01-27_

## Detailed Design (moved from README)

### Strategy Plugin System

**Goal**: Add new strategies without modifying core code.

**How it Works**:

1. **Define Strategy** (Python class):

```python
# packages/strategies/conventional/my_strategy.py

class MyStrategy(BaseStrategy):
    def on_candle(self, candle, timeframe):
        # Generate signals from technical, ML, orderbook
        signals = self.generate_signals()
        return self.aggregator.aggregate(signals)
```

2. **Configure Strategy** (YAML):

```yaml
# config/strategies/my_strategy.yaml

strategy:
  id: "my-strategy-001"
  name: "My Strategy"
  class: "MyStrategy" # Python class name

market:
  exchange: "mexc"
  symbol: "BTC/USDT"
  primary_timeframe: "1m"

parameters:
  # Strategy-specific parameters
```

3. **Run Strategy**:

```bash
uv run python -m apps.trader.main --config config/strategies/my_strategy.yaml
```

**Strategy automatically loaded** via `StrategyLoader` - no core code changes needed!

### Signal Framework

Strategies generate **Signal objects** (not simple strings):

```python
@dataclass
class Signal:
    type: SignalType          # BUY, SELL, CLOSE, PARTIAL_CLOSE
    source: SignalSource      # TECHNICAL, ML_MODEL, ORDERBOOK
    confidence: float         # 0.0 to 1.0
    reason: str               # Human-readable explanation
    metadata: dict            # Additional context
    close_percentage: float   # For partial closes (0.5 = 50%)
```

**Signal Sources**:

1. **Technical**: RSI, MACD, Bollinger Bands, True VWAP
2. **ML Model**: LSTM/RandomForest/XGBoost predictions
3. **Order Book**: Bid/ask imbalance, liquidity analysis

**Signal Aggregation**:

- **Voting**: Majority wins
- **Weighted**: Confidence-weighted average
- **Unanimous**: All sources must agree
- **Threshold**: Must exceed confidence threshold (e.g., 0.6)

**Example**:

```
Technical Signal: BUY (confidence 0.75) - "RSI oversold at 28.5"
ML Signal:        BUY (confidence 0.82) - "LSTM predicts 2.5% upward movement"
OrderBook Signal: BUY (confidence 0.68) - "68% bid dominance"

Aggregated Signal: BUY (confidence 0.75) - Weighted average exceeds threshold ✓
```

### Complex Exit Management

Exit conditions can be arbitrarily complex:

1. **Stop Loss**: Fixed percentage (e.g., -1%)
2. **Take Profit**: Tiered levels (e.g., 33% @ +2%, 33% @ +4%, 34% @ +6%)
3. **Trailing Stop**: Dynamic (e.g., trail by 0.5% from highest price)
4. **Time-Based**: Exit after X minutes if no profit
5. **ML-Based**: Exit when ML model predicts reversal

**Example Exit Flow**:

```
Entry: $42,165.75 (0.0475 BTC)
  ↓
Price reaches +2% → Close 33% (0.0157 BTC) ✓
  ↓
Price reaches +4% → Close 33% (0.0157 BTC) ✓
  ↓
Price reaches +6% → Close remaining 34% (0.0161 BTC) ✓

Total PNL: +$79.02 (+3.95%)
```

### Multi-Timeframe Support

Strategies can analyze **any number of timeframes** simultaneously:

```yaml
market:
  primary_timeframe: "1m" # Execution timeframe
  timeframes:
    - "1m" # Ultra-short term
    - "5m" # Short term
    - "15m" # Medium term
    - "1h" # Long term
```

**No hardcoded "HTF" or "LTF"** - fully dynamic!

Strategy receives candles tagged with their timeframe:

```python
def on_candle(self, candle, timeframe):
    if timeframe == "1m":
        # Primary timeframe - check for entry
    elif timeframe == "5m":
        # Confirmation timeframe - validate trend
```

### Machine Learning Integration

**Training Pipeline**:

1. **Data Loading** - Rolling window from database (last 30 days)
2. **Feature Engineering** - 60+ features (RSI, MACD, lags, VWAP, time)
3. **Model Training** - LSTM/RandomForest/XGBoost
4. **Evaluation** - Backtest on validation set, calculate metrics
5. **Deployment** - Hot-swap if better than current model
   ``
