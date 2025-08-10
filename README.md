# trade-bot

Spot crypto trading bot (BTC/USDT first) with a safety-first approach. Built with Python 3.11, Poetry, Docker, and GitHub Actions.

## Quickstart

```bash
git clone https://github.com/acid0ikario/trade-bot
cd trade-bot

# Optional: install Poetry
curl -sSL https://install.python-poetry.org | python3 -
export PATH="$HOME/.local/bin:$PATH"

poetry install
cp .env.example .env
cp config/config.example.yaml config/config.yaml

# Run tests
poetry run pytest -q
/home/repos/trade-bot/.venv/bin/python -m pytest -q

# Run (stub runner)
poetry run python -m bot.runner --paper --config config/config.yaml
```

### Docker

```bash
docker build -t trade-bot:dev .
docker run --rm --env-file .env -v $PWD/config:/app/config -v $PWD/data:/app/data trade-bot:dev python -m bot.runner --paper --config config/config.yaml
```

## Safety notes

* **Spot only.** No withdrawals will be supported.
* Guards (risk per trade, daily loss limits) arrive in later steps.

## Roadmap

1. Exchange wrapper (ccxt) + guardrails
2. Risk & position sizing (ATR)
3. Strategy (EMA/RSI) with candle-close signals
4. Paper engine + live runner
5. Backtester + metrics + artifacts
6. Nightly CI with regression issues
7. Go-live checklist

## CI Nightly Regression Checks

Nightly workflow runs a small backtest grid, evaluates metrics, and uploads artifacts.

- Artifacts: `data/artifacts/backtest_results.csv` and `data/artifacts/summary.json` uploaded as `nightly-artifacts`.
- Thresholds (override via repository Variables):
  - `SHARPE_THRESHOLD` (default `1.0`)
  - `MAX_DD_THRESHOLD` (default `-0.20`)
- On regression, a GitHub Issue is created using the Backtest Regression template with key metrics and links to artifacts.

## Optimizer and A/B Backtests

Optimize strategy defaults from prior backtests and compare filter variants.

- Generate optimized defaults from CSV:

```bash
poetry run python -m bot.optimize --results data/artifacts/backtest_results.csv
# Outputs: data/artifacts/optimized_defaults.yaml
```

- Run A/B comparisons (baseline, ADX only, Volume only, both):

```bash
poetry run python -m bot.optimize --ab --symbol BTC/USDT --timeframe 1h --years 1
# Outputs: data/artifacts/ab_results.csv and data/artifacts/ab_summary.txt
```

- Adopt optimized defaults:
  - Open `data/artifacts/optimized_defaults.yaml` and merge keys into your `config/config.yaml` under the same names (ema_fast, ema_slow, rsi bounds, atr_k, risk_rr).
  - Optionally enable filters by setting `enable_adx` and/or `enable_vol_filter` to true and adjust `volume_factor`.

