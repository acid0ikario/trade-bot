You are acting as a senior Python quant developer. Implement the trading strategy logic and its tests.

# Context
- Project: trade-bot. The exchange wrapper, risk management, and position sizing modules are in place.
- The strategy operates on OHLCV candles loaded into a pandas DataFrame (time ascending).
- Indicators needed: EMA fast, EMA slow, RSI. Parameters come from AppConfig (ema_fast, ema_slow, rsi_period, rsi_buy_min/max).

# Goals
Create a strategy module that generates long-entry signals based on classic trend and momentum filters, without lookahead bias.

# Tasks
1. **Implementation** (`src/bot/strategy.py`):
   - Use pandas (or ta) to compute:
     * `EMAfast` with span `ema_fast`.
     * `EMAslow` with span `ema_slow`.
     * `RSI` with period `rsi_period`.
   - Define a function `generate_signal(df: pandas.DataFrame, cfg: AppConfig) -> str | None`:
     * Takes a DataFrame with columns `['open','high','low','close','volume']`, sorted by time.
     * Uses only the last *closed* candle (`df.iloc[-2]`) for signals; do not peek at the current forming candle.
     * Criteria for a **buy** signal:
       - `EMAfast` > `EMAslow` on the latest closed candle.
       - `RSI` between `cfg.rsi_buy_min` and `cfg.rsi_buy_max` (inclusive).
       - Close price > `EMAfast`.
       - A “pullback” confirmation: the previous candle’s close is lower than the close two candles ago (`df.iloc[-3].close > df.iloc[-2].close`).
     * If all criteria pass, return `"buy"`; otherwise return `None`. Do not implement shorts yet.
   - Exit logic is handled elsewhere; your function does **not** place orders.

2. **No lookahead bias**:
   - All computations must use past data only. Avoid using the current candle (`df.iloc[-1]`) as it is still forming.

3. **Tests** (`tests/test_strategy.py`):
   - Create synthetic OHLCV DataFrames where you control EMA crossings and RSI values.
   - Verify that `generate_signal` returns `"buy"` only on candles that meet all criteria.
   - Verify that it returns `None` when any condition fails.
   - Ensure that modifying the latest (incomplete) candle does not change the signal.

# Acceptance criteria
- Strategy module can be imported without errors.
- Tests cover positive and negative cases and pass via `pytest`.
- No lookahead bias: the function never references `df.iloc[-1]`.
