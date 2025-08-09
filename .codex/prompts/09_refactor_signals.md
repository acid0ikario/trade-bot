You are acting as a performance-minded Python developer. Refactor indicator and signal computation for speed and clarity without changing behaviour.

Context

- Current `generate_signal` recomputes indicators repeatedly and directly on demand.
- Project uses pandas-based indicators (EMA/RSI) and may add ADX/volume filters.

Goals

- Compute indicators once per DataFrame, expose reusable helpers, and avoid lookahead.
- Preserve signal semantics (use last CLOSED candle).

Tasks

1) `src/bot/strategy.py`
- Add `calculate_indicators(df, cfg) -> DataFrame`:
  - Returns a copy with columns: `ema_fast`, `ema_slow`, `rsi`.
  - If filters enabled by config: also compute `adx`, `vol_sma`.
  - Use vectorized operations only; no Python loops.
  - Include docstring explaining inputs/outputs and lookahead safety.
- Refactor `generate_signal` to:
  - Use precomputed columns when present, else call `calculate_indicators`.
  - Enforce candle-close policy (ignore the last incomplete bar by default).
  - Keep existing entry/exit rules intact.
- Add small helpers for readability:
  - `_trend_up(row)`, `_rsi_in_range(row, cfg)`, `_is_pullback(df)`.

2) Tests
- Add fixtures with deterministic OHLCV data and precomputed indicators.
- Verify signals are identical to baseline for the same dataset (golden master style).
- Optional: simple timing check to show fewer indicator computations across multiple calls.

Acceptance criteria

- No change in generated signals vs baseline tests.
- Clear, documented code; helpers have docstrings and type hints.
- No lookahead bias introduced; last bar handling is explicit.