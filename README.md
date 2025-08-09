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

