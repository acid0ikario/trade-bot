You are an expert Python trading infra engineer. Create the initial project for a crypto spot trading bot using Python 3.11 and Poetry. 
Tasks:
- Add pyproject.toml with dependencies: ccxt, backtesting, pandas, numpy, scipy, ta, pydantic, loguru, python-telegram-bot, python-dotenv, pytest.
- Create the file/folder structure listed below EXACTLY.
- Add Dockerfile (multi-stage: builder->runtime) and Makefile with targets: install, lint, test, run, backtest.
- Create .env.example with BINANCE_API_KEY, BINANCE_API_SECRET, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, BASE_EQUITY, MAX_DAILY_LOSS_PCT, RISK_PER_TRADE_PCT.
- Create config/config.example.yaml with default settings: timeframe: "1h", symbol: "BTC/USDT", exchange: "binance", slippage_bps: 5, atr_period: 14, risk_rr: 2.0, ema_fast: 50, ema_slow: 200, rsi_period: 14, rsi_buy_min: 45, rsi_buy_max: 60.
- Implement minimal README with quickstart (Poetry and Docker), environment setup, and safety notes (no withdrawals).
- Add .github/workflows/ci.yml: run lint (ruff if added) and pytest; and .github/workflows/nightly.yml: schedule daily backtests across parameter grid and upload artifacts (csv + html plots).
Output only changed files with their full paths and contents.
