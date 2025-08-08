You are acting as a performance-minded Python developer. Refactor signal computation for speed and clarity without changing behaviour.

Context

    generate_signal currently recomputes indicators each call.

Goals

    Compute indicators once per DataFrame; modularize checks.

Tasks

    src/bot/strategy.py:

        Add calculate_indicators(df, cfg) -> DataFrame:
        • returns copy with columns: ema_fast, ema_slow, rsi (and optionally adx, vol_sma if filters enabled).
        • vectorized ops only; no loops.

        Modify generate_signal to:
        • use precomputed columns when present; otherwise call calculate_indicators.
        • keep the same entry rules and candle-close policy (use last CLOSED candle).

    Helpers

    _trend_up(row), _rsi_in_range(row, cfg), _is_pullback(df) for readability.

    Tests

    Signals identical to pre-refactor on fixed datasets.

    (Optional) basic timing check showing fewer computations on repeated calls.

Acceptance criteria

    No change in signals vs. baseline tests.

    Simpler, faster code with docstrings for helpers.

    No lookahead bias introduced.

––––––––––––––––––––––––––––––––––––