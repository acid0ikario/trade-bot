You are acting as a quantitative analyst. Use nightly backtest results to tune defaults and add optional entry filters.

Context

    Nightly CSV with results is available; plots saved as artifacts.

    Strategy uses EMA/RSI defaults.

Goals

    Recommend new defaults from top quartile; implement ADX and volume filters behind flags; run A/B comparisons.

Tasks

    Optimization script (src/bot/optimize.py):

        Read data/artifacts/backtest_results.csv.

        Select top quartile by Sharpe and (secondarily) lower drawdown.

        For each parameter (ema_fast, ema_slow, rsi bounds, atr_k, risk_rr):
        • derive median/mode across the top quartile
        • write data/artifacts/optimized_defaults.yaml.

    New filters in src/bot/strategy.py:

        Add config fields to AppConfig:
        • use_adx_filter: bool = False
        • use_volume_filter: bool = False
        • volume_factor: float = 1.5

        ADX(14) > 20 required when use_adx_filter.

        Volume surge: volume > SMA(volume, 20) * volume_factor when use_volume_filter.

        Apply only if flags are true; keep baseline intact when false.

    A/B backtests:

        Run 4 variants: baseline, ADX only, volume only, both.

        Write data/artifacts/ab_results.csv with Sharpe, MaxDD, Winrate, ProfitFactor, Expectancy, CAGR.

        Short summary in README (table + 2–3 bullet insights).

    Update defaults

    If optimized_defaults.yaml exists, update config/config.example.yaml with new default params (not the new filters; leave them disabled).

Acceptance criteria

    Optimizer outputs recommended defaults.

    Filters are configurable via YAML.

    A/B results saved and summarized in README.

    Baseline behaviour unchanged when flags off.

––––––––––––––––––––––––––––––––––––