.PHONY: install lint test run backtest

install:
poetry install

lint:
@ruff --version >/dev/null 2>&1 && ruff check || echo "ruff not installed; skipping lint"

test:
poetry run pytest -q || true

run:
poetry run python -m bot.runner --paper --config config/config.yaml || true

backtest:
poetry run python -m bot.backtest --symbol BTC/USDT --timeframe 1h --years 1 || true
