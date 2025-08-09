You are acting as a senior trading infrastructure engineer. Extend the runner to support live trading with robust safety features.

Context

- Project: trade-bot (Python 3.11, ccxt, loguru, pydantic). Paper mode exists.
- Exchange wrapper enforces symbol whitelist and notional caps.
- Risk module exposes position sizing and daily loss constraints.

Goals

- Add live trading mode using real API keys from environment.
- Support dry-run to print intended actions without placing orders.
- Implement a kill switch that halts new orders when daily loss exceeds a configured limit.

Tasks

1) Runner changes: `src/bot/runner.py`
- Add CLI flags: `--live`, `--dry-run` (mutually compatible: live+dry-run is allowed for staging).
- When `--live`:
  - Load API keys from env via `load_config()` and pass to `Exchange`.
  - Determine equity from free quote currency balance (e.g., USDT) using `Exchange.get_balance()` or `BASE_EQUITY` fallback.
  - Validate `symbols_whitelist` and `max_notional_per_trade_usdt` are present and non-zero.
- Core loop (poller):
  - For each `symbol` in `cfg.symbols_whitelist`:
    - Fetch latest candles with `Exchange.fetch_ohlcv()` and compute signal via `strategy`.
    - If entry signal:
      - Compute position size via `risk.position_size(equity, cfg, price)`.
      - Derive SL/TP (e.g., ATR-based with `cfg.atr_k` and `cfg.risk_rr`).
      - If `--dry-run`: log intended order and notification without placing real orders.
      - Else: place market order then OCO via `place_oco_takeprofit_stoploss()`.
      - Log order ids and send Telegram notification if enabled.
  - Track open orders and cancel the opposite leg when one fills (simple polling of order statuses).
- Kill switch:
  - If daily PnL <= `-MAX_DAILY_LOSS_PCT * equity`, skip new entries, log, and notify.

2) README updates (Go-Live Checklist)
- Add a section documenting:
  - API key requirements: Binance Spot only, no withdrawal permissions.
  - Environment variables required and how to set them.
  - Pre-flight: run paper for multiple days → live with `--dry-run` → live trading.
  - Risk validation: confirm `max_notional_per_trade_usdt` and whitelist.
  - Monitoring: logs and Telegram alerts.

3) Tests
- Add unit tests for runner logic using monkeypatches to:
  - Force a buy signal and assert `create_market_buy` and OCO are called when not dry-run.
  - Assert no order placement when kill switch engaged.
  - Assert dry-run logs intent and does not call exchange order functions.

Acceptance criteria

- In live mode (non-dry-run), orders are placed and logged; in dry-run, only intents are logged.
- Kill switch prevents new orders once daily loss exceeds limit.
- README updated with a clear go-live checklist.
- No withdrawal functionality added anywhere.