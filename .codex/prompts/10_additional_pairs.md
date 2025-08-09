You are acting as a multi-asset trading engineer. Enable trading multiple pairs with correlation-aware limits.

Context

- Currently single pair. We want to add ETH/USDT and BNB/USDT alongside BTC/USDT.
- Paper and live code must be able to handle multiple concurrent symbols.

Goals

- Multi-pair trading with per-pair caps and a correlation guard to avoid overexposure.

Tasks

1) Config updates
- Update `config/config.example.yaml`:
  - `symbols_whitelist: ["BTC/USDT","ETH/USDT","BNB/USDT"]`
  - `max_notional_usdt_per_pair: 200`
  - `max_correlated_trades: 2`
  - `correlation_threshold: 0.85`
- Optionally support `config/pairs.yaml` for per-pair caps, e.g.: `BTC:200, ETH:150, BNB:100`.
- Extend `AppConfig` in `src/bot/config.py` to include the new fields with sensible defaults; loading `pairs.yaml` is optional and should fall back to the global cap.

2) Broker/exchange support
- Ensure paper broker and live exchange tracking can hold multiple open positions keyed by symbol.
- Enforce per-pair notional caps and global `max_open_trades` across all symbols.

3) Correlation guard
- Before opening a trade for `symbol_new`, compute Pearson correlation of last N returns (e.g., 100 bars) between `symbol_new` and each open position’s symbol using available OHLCV.
- If correlation > threshold and current count of correlated positions >= `max_correlated_trades`, skip the new trade and log the reason.

4) Runner changes
- Iterate over each whitelisted symbol per loop.
- Apply correlation and risk guards across combined PnL and open positions.

5) Tests: `tests/test_multi_pairs.py`
- Create synthetic OHLCV for correlated and uncorrelated series.
- Verify the guard blocks opening beyond the correlation cap while allowing uncorrelated positions up to `max_open_trades`.

Acceptance criteria

- Multi-pair trading works with per-pair caps.
- Correlation guard enforced according to thresholds.
- Tests pass for edge and typical cases.