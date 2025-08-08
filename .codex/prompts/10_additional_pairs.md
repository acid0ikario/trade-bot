You are acting as a multi-asset trading engineer. Enable trading multiple pairs with correlation-aware limits.

Context

    Currently single pair. We want ETH/USDT, BNB/USDT in addition to BTC/USDT.

Goals

    Multi-pair trading with per-pair caps and correlation guard to avoid overexposure.

Tasks

    Config updates:

        config/config.example.yaml:
        • symbols_whitelist: ["BTC/USDT","ETH/USDT","BNB/USDT"]
        • max_notional_usdt_per_pair: 200
        • max_correlated_trades: 2
        • correlation_threshold: 0.85

        Optionally config/pairs.yaml per-pair caps (e.g., BTC:200, ETH:150, BNB:100).

    Broker/exchange support:

        PaperBroker and live tracking must allow multiple open positions keyed by symbol.

        Enforce per-pair notional and global max_open_trades.

    Correlation guard:

        Before opening a trade for symbol_new, compute Pearson correlation of last N returns (e.g., 100 bars) vs. each open position’s symbol.

        If correlation > threshold and current count of correlated positions >= max_correlated_trades → skip trade and log reason.

    Runner changes:

        Iterate over each whitelisted symbol per loop.

        Apply correlation guard and risk guards across the combined PnL.

    Tests (tests/test_multi_pairs.py):

        Synthetic OHLCV for correlated and uncorrelated series.

        Verify guard blocks opening beyond correlation cap; allow uncorrelated positions up to max_open_trades.

Acceptance criteria

    Multi-pair works with per-pair caps.

    Correlation guard enforced.

    Tests pass for edge and typical cases.