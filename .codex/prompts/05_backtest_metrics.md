You are acting as a Python quant backtester. Implement the backtesting engine and metrics.

# Context
- The strategy and risk modules are implemented; the exchange wrapper is used only for live data.
- Historical data can be loaded via `ccxt` or provided as CSV for tests.
- We need a flexible backtest engine with comprehensive metrics and artifact outputs.

# Goals
Allow grid-search backtests over parameter combinations, calculate performance metrics, and persist results.

# Tasks
1. **Backtest engine** (`src/bot/backtest.py`):
   - Provide a function `run_backtest(symbol: str, timeframe: str, years: int, cfg: AppConfig, param_grid: dict[str,list], data_loader=None) -> list[dict]`:
     * If `data_loader` is None, download historical data from ccxt’s Binance spot for the given `symbol` and `timeframe` (respect rate limits). Otherwise, call `data_loader(symbol, timeframe, years)`.
     * For each combination in `param_grid` (e.g. ema_fast values [20,50], ema_slow [100,200], rsi bounds, atr_k, risk_rr), create a copy of `cfg` with those overrides.
     * Simulate the strategy: loop through candles, generate signals, compute qty, update positions, track equity curve. Apply fees and slippage per config. Stop trading when kill_switch triggers.
     * Collect metrics (see below) and return a list of dicts, each containing parameters, metrics, and the equity curve.

   - Provide a CLI:  
     ```
     python -m bot.backtest --symbol BTC/USDT --timeframe 1h --years 2 --grid config/backtest_grid.yaml
     ```
     The YAML file should map parameter names to lists. If not provided, use a default small grid.

2. **Metrics module** (`src/bot/metrics.py`):
   - Implement functions:
     * `cagr(equity: list[float], years: float) -> float`: compounded annual growth rate.
     * `max_drawdown(equity: list[float]) -> float`: maximum percentage drop from a peak.
     * `winrate(trades: list[Trade]) -> float`: fraction of trades with positive PnL.
     * `profit_factor(trades: list[Trade]) -> float`: total profit / total loss.
     * `expectancy(trades: list[Trade]) -> float`: average PnL per trade.
     * `avg_trade(trades: list[Trade]) -> float`: mean absolute PnL.
     * Use the existing `sharpe` helper for Sharpe ratio.

   - Ensure no division-by-zero errors. If no trades or undefined metrics, return 0.0.

3. **Artifacts & reporting**:
   - For each run, write a CSV row to `data/artifacts/backtest_results.csv` with parameter values and metric outputs.
   - Save an equity curve plot (PNG or HTML) using matplotlib or plotly in `data/artifacts/equity_<params_hash>.png`.
   - Optionally, generate a summary HTML report (table of results) for easy viewing.

4. **Tests** (`tests/test_backtest_metrics.py`):
   - Provide synthetic equity curves (e.g. steadily increasing, flat, random) and verify metrics:
     * CAGR of a series doubling in one year is ~100%.
     * Max drawdown of a monotonic series is 0.
     * Winrate and profit factor for known trade sequences.
   - Use a minimal `param_grid` and short random walk to ensure `run_backtest` returns a list with expected fields.

# Acceptance criteria
- Backtest engine runs through full grids without crashing.
- Metrics compute correct values on simple inputs.
- CSV results and equity plots are saved as artifacts.
- All tests pass with `pytest`.
