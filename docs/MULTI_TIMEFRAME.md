# Multi-Timeframe Trading Guide

## Overview

The strategy engine now supports **true multi-timeframe analysis**, allowing you to analyze different timeframes simultaneously for better trade confirmation and filtering.

## How It Works

### 1. Configuration

Specify multiple timeframes in your strategy YAML:

```yaml
market:
  exchange: "mexc"
  symbol: "BTC/USDT"
  primary_timeframe: "5m" # Main decision timeframe
  timeframes:
    - "1m" # Fast signals
    - "5m" # Primary analysis
    - "15m" # Trend filter
    - "1h" # Major direction
```

### 2. Indicator Calculation

Configure which timeframes each indicator should be calculated on:

```yaml
indicators:
  # RSI on multiple timeframes
  - name: "RSI"
    params:
      period: 14
    timeframes: ["1m", "5m", "15m"]

  # EMA on higher timeframes only
  - name: "EMA"
    params:
      period: 20
    timeframes: ["15m", "1h"]
```

**Note:** If `timeframes` is omitted, the indicator is calculated only on `primary_timeframe`.

### 3. Naming Convention

Indicators are stored with the format: `{INDICATOR}_{TIMEFRAME}`

Examples:

- `RSI_1m` - RSI calculated on 1-minute candles
- `RSI_5m` - RSI calculated on 5-minute candles
- `EMA_15m` - EMA calculated on 15-minute candles
- `SMA_1h` - SMA calculated on 1-hour candles

### 4. Using in Conditions

Reference indicators by their timeframe-suffixed names:

```yaml
entry:
  mode: "AND"
  conditions:
    - "RSI_1m < 30" # 1m oversold
    - "RSI_5m < 40" # 5m oversold
    - "PRICE > EMA_15m" # Above 15m trend
    - "EMA_15m > EMA_1h" # Bullish trend hierarchy
```

## Data Flow

### WebSocket Streaming

Each timeframe gets its own independent stream:

```python
# Automatically started for all configured timeframes
- watch_ohlcv(symbol, "1m")   → New candle every minute
- watch_ohlcv(symbol, "5m")   → New candle every 5 minutes
- watch_ohlcv(symbol, "15m")  → New candle every 15 minutes
- watch_ohlcv(symbol, "1h")   → New candle every hour
```

### History Storage

Candles are stored separately per timeframe:

```python
self.history = {
    "1m":  [candle1, candle2, ...],   # 1-minute candles
    "5m":  [candle1, candle2, ...],   # 5-minute candles
    "15m": [candle1, candle2, ...],   # 15-minute candles
    "1h":  [candle1, candle2, ...],   # 1-hour candles
}
```

### Signal Generation

Signals are only generated when the **primary_timeframe** candle arrives to avoid duplicates:

```python
def on_candle(self, candle, timeframe):
    # Update history for this timeframe
    self.update_history(candle, timeframe)

    # Only generate signals on primary timeframe
    if timeframe != self.primary_timeframe:
        return

    # Calculate indicators across all timeframes
    self._calculate_indicators()

    # Generate and execute signals
    signals = self.generate_signals(candle)
```

## Strategy Examples

### Example 1: Trend Confirmation

Use higher timeframes to filter trades:

```yaml
# Only enter when ALL timeframes align
entry:
  mode: "AND"
  conditions:
    - "RSI_5m < 30" # Entry signal on primary
    - "PRICE > EMA_15m" # Above medium-term trend
    - "PRICE > SMA_1h" # Above long-term trend
```

### Example 2: Divergence Detection

Compare same indicator across timeframes:

```yaml
entry:
  mode: "AND"
  conditions:
    - "RSI_1m < RSI_5m" # 1m more oversold than 5m
    - "RSI_5m < RSI_15m" # Momentum building
    - "RSI_15m < 50" # But not overbought yet
```

### Example 3: Trend Hierarchy

Ensure all trend indicators align:

```yaml
entry:
  mode: "AND"
  conditions:
    - "EMA_5m > EMA_15m" # Fast > Medium
    - "EMA_15m > EMA_1h" # Medium > Slow
    - "EMA_1h > SMA_1h" # Exponential > Simple (acceleration)
```

## Backward Compatibility

**Single-timeframe strategies continue to work unchanged:**

If you configure:

```yaml
timeframes: ["5m"]
indicators:
  - name: "RSI"
    params:
      period: 14
```

The indicator is available as **both**:

- `RSI_5m` (explicit)
- `RSI` (implicit for compatibility)

So existing conditions like `"RSI < 30"` continue to work.

## Best Practices

### 1. Choose Complementary Timeframes

Use timeframes that are multiples of each other:

- ✅ Good: 1m, 5m, 15m, 1h (clean multiples)
- ❌ Avoid: 3m, 7m, 11m (odd intervals)

### 2. Primary Timeframe Selection

Choose based on trading style:

- **Scalping**: 1m or 5m primary
- **Day Trading**: 5m or 15m primary
- **Swing Trading**: 1h or 4h primary

### 3. Use Higher TFs for Filtering

Common pattern:

- **Primary TF**: Entry/exit signals
- **Higher TFs**: Trend filters and confirmation
- **Lower TFs**: Precise entry timing

### 4. Avoid Over-Complicating

More timeframes ≠ better results:

- 2-3 timeframes: Usually sufficient
- 4-5 timeframes: Advanced strategies
- 6+ timeframes: Likely overfit

### 5. Performance Considerations

Each timeframe:

- Adds a WebSocket stream
- Stores separate history
- Calculates separate indicators

For resource-constrained environments, limit to 2-3 timeframes.

## Implementation Details

### Database Storage

All timeframes share the same `ohlcv_data` table with composite key:

```sql
UNIQUE(exchange, symbol, timeframe, timestamp)
```

This means:

- No duplication across strategies
- Efficient storage
- Fast queries per timeframe

### WebSocket → Database → Strategy

```
Exchange WebSocket
    ↓
WebSocketManager (packages/websocket/websocket.py)
    ↓
Database (ohlcv_data table)
    ↓
Strategy.on_candle(candle, timeframe)
    ↓
Strategy.history[timeframe].append(candle)
    ↓
_calculate_indicators() [on primary_timeframe candle only]
    ↓
generate_signals()
```

### Indicator Calculation Logic

From `packages/strategies/yaml_strategy.py`:

```python
def _calculate_indicators(self) -> None:
    for indicator_config in self.indicator_configs:
        name = indicator_config['name']
        params = indicator_config.get('params', {})

        # Get timeframes for this indicator
        indicator_timeframes = indicator_config.get('timeframes', [self.primary_timeframe])

        for tf in indicator_timeframes:
            history = self.history.get(tf, [])

            # Calculate and store as "{NAME}_{TF}"
            value = calculate_indicator(history, params)
            self.indicators[f"{name}_{tf}"] = value
```

## Troubleshooting

### Indicator Not Found

**Error:** `KeyError: 'RSI_15m'`

**Cause:** Indicator not configured for that timeframe

**Fix:**

```yaml
indicators:
  - name: "RSI"
    timeframes: ["1m", "5m", "15m"] # Add 15m
```

### Insufficient Data

**Behavior:** Conditions not evaluating initially

**Cause:** Higher timeframes need more time to accumulate data

**Expected:**

- 1m: Ready after ~1 minute
- 5m: Ready after ~5 minutes
- 1h: Ready after ~1 hour

**Solution:** Be patient, or run backfiller to pre-populate history

### No Signals Generated

**Cause:** Signals only generated on primary_timeframe candles

**Check:**

- Ensure `primary_timeframe` is in `timeframes` list
- Verify WebSocket is streaming primary timeframe
- Check logs for primary timeframe candle updates

## Multi-Timeframe with ML Strategies

### How ML Works Across Timeframes

Machine Learning indicators (PRICE_PREDICTION, ARIMA_PREDICTION, RF_PREDICTION) work **identically** to technical indicators with multi-timeframe support:

```yaml
indicators:
  - name: "PRICE_PREDICTION"
    params:
      lookback: 20
      horizon: 5
    timeframes: ["1m", "5m", "15m"]

  - name: "ARIMA_PREDICTION"
    params:
      order: [1, 1, 1]
      horizon: 3
    timeframes: ["5m", "15m"]
```

This creates:

- `PRICE_PREDICTION_1m` - Prediction from 1-minute candles
- `PRICE_PREDICTION_5m` - Prediction from 5-minute candles
- `PRICE_PREDICTION_15m` - Prediction from 15-minute candles
- `ARIMA_PREDICTION_5m` - ARIMA from 5-minute candles
- `ARIMA_PREDICTION_15m` - ARIMA from 15-minute candles

### Key Differences for ML

**1. Data Requirements**

ML models need MORE data than technical indicators:

| Indicator        | Minimum Candles | 5m Timeframe | 15m Timeframe |
| ---------------- | --------------- | ------------ | ------------- |
| RSI              | 14              | ~70 minutes  | ~210 minutes  |
| EMA              | 20              | ~100 minutes | ~300 minutes  |
| PRICE_PREDICTION | 20              | ~100 minutes | ~300 minutes  |
| ARIMA_PREDICTION | 30              | ~150 minutes | ~450 minutes  |
| RF_PREDICTION    | 50+             | ~250 minutes | ~750 minutes  |

**2. Prediction Horizons Scale with Timeframe**

```yaml
# Same horizon parameter = different time windows
- name: "PRICE_PREDICTION"
  params:
    horizon: 5 # Predict 5 candles ahead
  timeframes: ["1m", "5m", "15m"]
```

Results in:

- `PRICE_PREDICTION_1m`: Predicts 5 minutes ahead (5 × 1m)
- `PRICE_PREDICTION_5m`: Predicts 25 minutes ahead (5 × 5m)
- `PRICE_PREDICTION_15m`: Predicts 75 minutes ahead (5 × 15m)

**3. ML Consensus Strategies**

Combine multiple ML models across timeframes for robust signals:

```yaml
entry:
  mode: "AND"
  conditions:
    # All timeframes must predict upward movement
    - "PRICE_PREDICTION_1m > PRICE"
    - "PRICE_PREDICTION_5m > PRICE * 1.003" # Require +0.3%
    - "PRICE_PREDICTION_15m > PRICE"

    # Multiple models on primary timeframe must agree
    - "ARIMA_PREDICTION_5m > PRICE"
    - "RF_PREDICTION_5m > PRICE"
```

### ML Multi-Timeframe Patterns

**Pattern 1: Cascade Prediction**

```yaml
# Each higher TF predicts even higher prices
conditions:
  - "PRICE_PREDICTION_1m > PRICE"
  - "PRICE_PREDICTION_5m > PRICE_PREDICTION_1m"
  - "PRICE_PREDICTION_15m > PRICE_PREDICTION_5m"
```

Interpretation: Momentum accelerating across all timeframes = strong trend

**Pattern 2: Divergence Detection**

```yaml
# Short-term vs long-term disagreement
conditions:
  - "PRICE_PREDICTION_1m > PRICE * 1.01" # 1m very bullish
  - "PRICE_PREDICTION_15m < PRICE" # 15m bearish
```

Interpretation: Counter-trend opportunity (scalp against main trend)

**Pattern 3: Multi-Model Ensemble**

```yaml
# Require agreement from multiple ML models on same TF
conditions:
  - "PRICE_PREDICTION_5m > PRICE"
  - "ARIMA_PREDICTION_5m > PRICE"
  - "RF_PREDICTION_5m > PRICE"
```

Interpretation: High confidence when different algorithms agree

**Pattern 4: Trend Alignment**

```yaml
# ML predictions must form bullish hierarchy
conditions:
  - "PRICE_PREDICTION_1m > PRICE"
  - "ARIMA_PREDICTION_5m > ARIMA_PREDICTION_15m" # 5m more bullish than 15m
  - "PRICE > EMA_15m" # Above technical trend
```

Interpretation: All trend indicators aligned = low-risk entry

### ML-Specific Best Practices

**1. Start with Primary Timeframe Only**

Before adding multi-TF, validate ML model works on single timeframe:

```yaml
# Step 1: Test single timeframe
timeframes: ["5m"]
indicators:
  - name: "PRICE_PREDICTION"
    params:
      lookback: 20
      horizon: 5
```

**2. Add Higher Timeframes Gradually**

```yaml
# Step 2: Add one higher timeframe
timeframes: ["5m", "15m"]
indicators:
  - name: "PRICE_PREDICTION"
    timeframes: ["5m", "15m"]
```

**3. Use Higher TFs for Filtering**

Short TF = signals, higher TF = filters:

```yaml
entry:
  mode: "AND"
  conditions:
    - "PRICE_PREDICTION_5m > PRICE * 1.005" # Signal from primary
    - "PRICE_PREDICTION_15m > PRICE" # Filter from higher TF
```

**4. Adjust Lookback for Timeframe**

Shorter TF = shorter lookback, longer TF = longer lookback:

```yaml
# Bad: Same lookback on all TFs
- name: "PRICE_PREDICTION"
  params:
    lookback: 20
  timeframes: ["1m", "15m"]

# Good: Adjust lookback per TF
- name: "PRICE_PREDICTION"
  params:
    lookback: 20
  timeframes: ["1m"] # 20 minutes of data

- name: "PRICE_PREDICTION"
  params:
    lookback: 50
  timeframes: ["15m"] # 750 minutes of data
```

**Note:** Current implementation doesn't support per-TF params. Use separate indicator configs:

```yaml
indicators:
  - name: "PRICE_PREDICTION"
    params:
      lookback: 20
    timeframes: ["1m", "5m"]

  # Different params for higher TF (future enhancement)
  # For now, same params applied to all specified timeframes
```

**5. Consider Computational Cost**

Each ML model × timeframe adds CPU load:

- 3 timeframes × 3 ML models = 9 calculations per candle
- Random Forest especially expensive (tree ensemble)
- Monitor latency: should be < candle duration

**6. Backtest Extensively**

ML multi-TF strategies are complex - backtest before live:

```bash
# Test with backtester
uv run python -m apps.backtester.main \
  --config config/strategies/btc_multi_tf_ml_ensemble.yaml \
  --days 30
```

### Example Strategy

See [btc_multi_tf_ml_ensemble.yaml](../config/strategies/btc_multi_tf_ml_ensemble.yaml) for a complete example that demonstrates:

- PRICE_PREDICTION on 3 timeframes (1m, 5m, 15m)
- ARIMA on 2 timeframes (5m, 15m)
- Random Forest on primary timeframe (5m)
- Consensus logic requiring all models to agree
- Technical filters (RSI, EMA) for additional confirmation

## See Also

- [btc_multi_timeframe_example.yaml](../config/strategies/btc_multi_timeframe_example.yaml) - Technical multi-TF example
- [btc_multi_tf_ml_ensemble.yaml](../config/strategies/btc_multi_tf_ml_ensemble.yaml) - ML multi-TF example
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [WEBSOCKET.md](WEBSOCKET.md) - Real-time data streaming
- [DATABASE.md](DATABASE.md) - Data storage strategy
