You are acting as a senior Python trading infra engineer. Build the paper trading engine and extend the runner.

# Context
- The project has an exchange wrapper with retries, a risk module (stop losses and loss guards), a position sizer, and a strategy module (03).
- We need a realistic paper trading environment that logs trades, updates equity, and supports later transition to live trading.

# Goals
Simulate the execution of trades and manage the trading loop cleanly, using loguru and Telegram notifications.

# Tasks
1. **Paper trading engine** (`src/bot/paper.py`):
   - Create a `Trade` dataclass with fields: symbol, side ("buy"/"sell"), entry_price, stop_price, take_profit, qty, entry_time, exit_price (optional), exit_time (optional), pnl (optional).
   - Create a `PaperBroker` class with:
     * Properties: `equity` (float), `open_positions` (dict by symbol), `trade_log` (list of Trade).
     * Method `buy(symbol: str, price: float, qty: float, stop: float, tp: float)`:
       - Deduct fees (taker) from equity per config.
       - Add a Trade to `open_positions`.
     * Method `sell(symbol: str, price: float, qty: float)`:
       - Close the Trade in `open_positions`.
       - Compute PnL = (price - entry_price) * qty - fees.
       - Update equity accordingly and append to `trade_log`.
     * Method `update_prices(candles_df: pandas.DataFrame)`:
       - For each open trade, if `low` <= stop_price <= `high`, close at stop; if `high` >= take_profit >= `low`, close at tp.
   - Use config fees: `cfg.fees.maker` for limit orders; `cfg.fees.taker` for market. Apply slippage (bps) when filling orders.

2. **Runner main loop** (`src/bot/runner.py`):
   - Parse CLI args: `--paper` (bool), `--live` (bool), `--config` (path).
   - Load config and env; set up logger and notifier.
   - For paper mode:
     * Initialize `PaperBroker` with equity `env.BASE_EQUITY`.
     * In an infinite loop (or until a user-defined `max_iterations` in tests):
         1. Fetch last `N` candles using `exchange.fetch_ohlcv` (e.g. 200).
         2. Convert to DataFrame and compute indicators.
         3. Use `strategy.generate_signal(df, cfg)` to get a signal.
         4. If `"buy"`:
            - Use `position_size` to compute qty (use `equity` from broker).
            - Use `compute_stop` (or swing low) and config `risk_rr` to determine stop and take-profit.
            - Call `broker.buy(...)` to simulate.
         5. Call `broker.update_prices(df.tail(1))` to see if any stops/TPs hit on the latest candle.
         6. Use `risk.max_daily_loss_guard` and `risk.kill_switch` on realized PnL (trade_log).
         7. Sleep for a configurable delay (e.g. 60 seconds).
   - For live mode (to be implemented later), call exchange methods instead of paper broker.

3. **Logging & notifications**:
   - Log all entries/exits with loguru. Use notifier (Telegram) to send messages when positions open/close and when a loss guard triggers.
   - Store a trade log CSV under `data/trades/YYYYMMDD.csv` on exit.

4. **Tests** (`tests/test_paper_runner.py`):
   - Use monkeypatch to replace `exchange.fetch_ohlcv` with deterministic candles that trigger a buy and then hit a TP.
   - Use a tiny config and a short loop (max 3 iterations) to verify:
     * A trade is recorded in `trade_log`.
     * Equity increases by the expected amount after the TP.
     * Loss guard triggers when cumulative PnL drops below threshold.

# Acceptance criteria
- Paper trading simulates entries/exits correctly with fees and slippage.
- Runner loop respects risk guards and logs appropriately.
- Tests pass deterministically without network access.
