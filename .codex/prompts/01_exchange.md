You are acting as a senior Python trading infra engineer. Our project already includes a partially implemented Exchange wrapper in `src/bot/exchange.py`. Your job is to review and refine this wrapper to ensure it is robust, safe, and fully aligned with our requirements for Binance spot trading.

## Context
- This bot trades crypto on Binance **spot** only; no withdrawals are allowed.
- The wrapper must load API credentials from the environment via `EnvVars`, enforce a **symbol whitelist**, and respect a **max notional per trade** (`max_notional_per_trade_usdt`) defined in `config.yaml`.
- The current implementation provides methods like `get_price`, `fetch_ohlcv`, `get_balance`, `create_market_buy`, `create_market_sell`, and `place_oco_takeprofit_stoploss`, along with helper functions for quantity and price rounding.

## Goals
1. **Audit the existing code** in `src/bot/exchange.py` to identify missing logic or edge cases.
2. **Harden safety features**: enforce whitelist and notional caps, apply Binance lot-size and min-notional filters, and ensure no withdrawal functionality.
3. **Improve reliability**: implement exponential backoff for retryable ccxt errors (NetworkError, DDoSProtection, RateLimitExceeded, etc.), and wrap all failures in a custom `ExchangeError`.
4. **Provide comprehensive tests** that mock ccxt interactions and cover both happy and failure paths.

## Tasks
1. **Review and refine the Exchange class**:
   - Ensure API keys from `EnvVars` are used and sanitized (remove `None` values).
   - Confirm that `symbols_whitelist` and `max_notional_per_trade_usdt` in the loaded config are actively checked in every order-related method.
   - Verify that `load_markets()` is called (or retried) to obtain market filters, and add helper methods to parse LOT_SIZE, PRICE_FILTER, and MIN_NOTIONAL fields.
   - Revisit `_prepare_order_qty()` to floor quantities to step size, respect minimum quantity and notional constraints, and throw `ExchangeError` on invalid input (e.g., zero quantity, notional too high).

2. **Implement or enhance public methods**:
   - `get_price(symbol)`: fetch the last/close price from `fetch_ticker`, raise `ExchangeError` if price is missing, and wrap in retry logic.
   - `fetch_ohlcv(symbol, timeframe, limit)`: fetch candles and return as a list of [timestamp, open, high, low, close, volume]; wrap in retry logic.
   - `get_balance(quote)`: return the free balance of a currency; handle both top-level and nested dictionary formats returned by ccxt.
   - `create_market_buy` / `create_market_sell`: compute adjusted quantity via `_prepare_order_qty()`, log the order, and place a market order with retries.
   - `place_oco_takeprofit_stoploss`: simulate an OCO order by placing a limit sell at TP and a stop-limit sell at SL; round TP/SL to the nearest tick size, adjust quantity, and return both order IDs.

3. **Safety and reliability**:
   - Use an internal `_with_retries()` helper implementing exponential backoff (e.g., base delay 0.05 s doubling up to 1 s) for transient ccxt errors, and raise `ExchangeError` on non-retryable errors.
   - Normalize all ccxt exceptions into our custom `ExchangeError`.
   - Do not include any withdrawal methods in this wrapper.

4. **Unit tests** (`tests/test_exchange.py`):
   - Use pytest and monkeypatch to simulate ccxt responses without hitting the network.
   - Test success cases: price retrieval, OHLCV retrieval, balance retrieval, successful buys, sells, and OCO orders.
   - Test failure cases: symbol not whitelisted, quantity below minimum, notional cap exceeded, missing price in ticker, and correct handling of step-size flooring.
   - Test retry logic by having the mock raise a retryable error once before succeeding.

5. **Acceptance criteria**:
   - All methods in `Exchange` behave as specified and raise `ExchangeError` on invalid inputs or API errors.
   - Tests in `tests/test_exchange.py` pass locally (run with `poetry run pytest -q`).
   - The wrapper enforces whitelist and notional caps, adjusts quantities for market filters, uses exponential backoff on transient errors, and logs order actions via loguru.
