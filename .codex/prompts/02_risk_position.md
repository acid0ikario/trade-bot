You are acting as a senior Python trading infra engineer. Implement the risk management and position sizing modules and their tests for this repo.

# Context
- Project: trade-bot (Python 3.11, Poetry). The exchange wrapper is already implemented.
- The existing files `src/bot/risk.py` and `src/bot/position.py` are stubs created in the bootstrap phase.
- Tests for these modules do not exist yet.

# Goals
Provide robust functions to compute stop-loss levels, enforce daily loss limits, and size positions according to risk.

# Tasks
1. **risk.py** (`src/bot/risk.py`):
   - Keep the existing `compute_stop(entry, atr, k)` helper.
   - Add `stop_by_swing_low(prices: list[float], lookback: int = 20) -> float`:
     * Given a list of historical low prices (recent lows), return the minimum of the last `lookback` values. If the list is shorter than `lookback`, use the whole list.
     * Ensure the returned stop is positive; if no data is provided, raise a `ValueError`.
   - Add `max_daily_loss_guard(pnl_list: list[float], base_equity: float, max_loss_pct: float) -> bool`:
     * Compute cumulative PnL for the trading day from `pnl_list` (each entry could be positive or negative).
     * Return `True` if cumulative loss is less than or equal to `-(base_equity * max_loss_pct)`; otherwise return `False` to signal that trading should halt.
   - Add `kill_switch(pnl_list: list[float], base_equity: float, max_loss_pct: float) -> bool`:
     * Wrapper that simply returns `not max_daily_loss_guard(...)`. Helpful for the runner to decide whether to disable trading.
     * Include a docstring explaining its purpose.

2. **position.py** (`src/bot/position.py`):
   - Extend `position_size(entry: float, stop: float, equity: float, risk_pct: float, step: float = 0.0) -> float`:
     * Compute the dollar risk per trade: `risk_amount = equity * risk_pct`.
     * Compute per-unit risk as `abs(entry - stop)`; if per-unit risk is zero or negative, raise a `ValueError`.
     * The raw quantity is `risk_amount / per_unit_risk`.
     * If `step > 0`, floor the quantity to the nearest multiple of `step` (similar to exchange lot size rounding). Otherwise, return the raw quantity.
     * Ensure the returned quantity is strictly positive; raise `ValueError` if it becomes zero after flooring.
   - Update docstrings to describe the new parameter.

3. **Tests**:
   - Create `tests/test_risk.py` with pytest:
     * Test that `compute_stop` returns `entry - atr * k` and never negative.
     * Test `stop_by_swing_low` returns the minimum low in the last `lookback` prices, and that it raises if given an empty list.
     * Test `max_daily_loss_guard`:
       - Returns `True` when cumulative losses are within limit.
       - Returns `False` when cumulative losses exceed `-base_equity * max_loss_pct`.
     * Test `kill_switch` returns the logical inverse of `max_daily_loss_guard`.
   - Create `tests/test_position.py` with pytest:
     * Test that `position_size` returns the correct quantity for simple cases (e.g. entry=100, stop=95, equity=2000, risk_pct=0.01, step=0.1 → qty=4.0).
     * Test that flooring to `step` works: quantity is rounded down to nearest step.
     * Test that passing zero or negative per-unit risk raises a `ValueError`.
     * Test that a tiny step or large risk_pct does not produce zero or negative quantity.
   - Ensure these tests run quickly and do not depend on ccxt or network.

4. **Adjustments**:
   - If you need to import additional modules (e.g. `math` for flooring), add them at the top of the relevant files.
   - Make sure to run `poetry run pytest -q` locally; all tests should pass.
   - Update the prompts folder only if you change the spec (no changes required here).

# Acceptance criteria
- `src/bot/risk.py` and `src/bot/position.py` contain fully implemented functions with docstrings.
- `tests/test_risk.py` and `tests/test_position.py` exist and cover edge cases.
- `poetry run pytest -q` passes on all tests.
- Existing functionality in other modules remains unaffected.

Now implement these changes.
