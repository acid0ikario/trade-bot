You are acting as a quantitative analyst. Use nightly backtest results to tune defaults and add optional entry filters.

Context

- Nightly CSV with results is available under `data/artifacts/backtest_results.csv`; plots are saved as artifacts.
- Strategy uses EMA/RSI defaults; optional ATR parameters are present.

Goals

- Recommend new defaults from the top quartile of runs.
- Implement ADX and volume filters behind feature flags.
- Run A/B comparisons to quantify impact and summarize findings.

Tasks

1) Optimizer script: `src/bot/optimize.py`
- Read `data/artifacts/backtest_results.csv`.
- Validate required columns exist: `Sharpe`, `MaxDD`, `Winrate`, `ProfitFactor`, `CAGR`, and parameter columns (`ema_fast`, `ema_slow`, `rsi_buy_min`, `rsi_buy_max`, `atr_k`, `risk_rr`).
- Select the top quartile by Sharpe (break ties by higher MaxDD i.e., less negative drawdown).
- For each parameter, compute a robust central tendency (median for numeric, mode for discrete) across the top quartile.
- Write `data/artifacts/optimized_defaults.yaml` with the recommended values and a small provenance block (date, n_top, thresholds).

2) New filters in `src/bot/strategy.py`
- Extend `AppConfig` with:
  - `use_adx_filter: bool = False`
  - `use_volume_filter: bool = False`
  - `volume_factor: float = 1.5`
- Implement:
  - ADX(14) > 20 if `use_adx_filter`.
  - Volume surge filter if `use_volume_filter`: `volume > SMA(volume, 20) * volume_factor`.
- Apply filters only when flags are true; keep baseline logic identical otherwise.

3) A/B backtests
- Run 4 variants via the existing backtest harness: baseline, ADX only, volume only, both.
- Aggregate metrics into `data/artifacts/ab_results.csv` with columns: `variant, Sharpe, MaxDD, Winrate, ProfitFactor, Expectancy, CAGR`.
- Append a short Markdown summary to `README.md` with a small table and 2–3 bullet insights.

4) Update defaults
- If `optimized_defaults.yaml` exists, update `config/config.example.yaml` with the recommended defaults for existing fields only; keep new filter flags disabled by default.

Acceptance criteria

- Optimizer produces `optimized_defaults.yaml` with sensible values.
- Strategy exposes configurable filters controlled by YAML flags; when flags are false, baseline signals remain unchanged.
- A/B results are saved and summarized in README.
- No network calls in the optimizer; all inputs are local artifacts.