Implement src/bot/exchange.py:
- Binance spot only via ccxt with methods: get_balance(quote), get_price(symbol), fetch_ohlcv(symbol, timeframe, limit), create_market_buy(symbol, qty), create_market_sell(symbol, qty), create_oco_takeprofit_stoploss(symbol, qty, tp_price, sl_price) (simulate OCO if not available in spot).
- Enforce safety: no withdrawals; max notional per trade from config; symbol whitelist.
- Add robust retry with exponential backoff and rate-limit handling.
- Unit tests in tests/test_exchange.py using ccxt sandbox mocking (pytest + monkeypatch).
Return all new/changed files.
