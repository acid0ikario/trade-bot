import pandas as pd
import numpy as np

from bot.strategy import calculate_indicators, generate_signal
from bot.config import AppConfig


def make_df(n=60, seed=42):
    rng = np.random.default_rng(seed)
    # Uptrend base
    base = np.linspace(90, 110, n)
    noise = rng.normal(0, 0.1, n)
    close = base + noise
    open_ = close + rng.normal(0, 0.05, n)
    high = np.maximum(open_, close) + 0.2
    low = np.minimum(open_, close) - 0.2
    vol = rng.integers(100, 200, n).astype(float)

    df = pd.DataFrame({
        "open": open_.astype(float),
        "high": high.astype(float),
        "low": low.astype(float),
        "close": close.astype(float),
        "volume": vol,
    })
    # Force a pullback on the last closed candle (-2)
    df.loc[n-3, "close"] = df.loc[n-2, "close"] + 0.5  # -3 greater than -2
    return df


def make_cfg():
    return AppConfig(
        ema_fast=5,
        ema_slow=10,
        rsi_period=5,
        rsi_buy_min=0,
        rsi_buy_max=100,
        slippage_bps=100,  # allow tolerance for close vs EMA
        symbols_whitelist=["BTC/USDT"],
        max_notional_per_trade_usdt=10000,
    )


def test_generate_signal_precomputed_vs_on_the_fly():
    df = make_df()
    cfg = make_cfg()

    # On-the-fly computation
    s1 = generate_signal(df.copy(), cfg)

    # Precompute once and reuse
    df_ind = calculate_indicators(df.copy(), cfg)
    s2 = generate_signal(df_ind.copy(), cfg)

    assert s1 == s2

    # Repeated calls should not change the outcome and should work with precomputed
    for _ in range(5):
        assert generate_signal(df_ind, cfg) == s2
        assert generate_signal(df, cfg) == s1


def test_no_lookahead_last_closed_candle():
    df = make_df()
    cfg = make_cfg()

    # Baseline signal
    base_sig = generate_signal(df.copy(), cfg)

    # Modify the last (incomplete) bar significantly; signal should still use -2
    df2 = df.copy()
    df2.loc[df2.index[-1], "close"] = df2.loc[df2.index[-1], "close"] + 1.23

    # Even with changed last bar, signal should be identical
    assert generate_signal(df2, cfg) == base_sig

    # Also when indicators are precomputed
    df2_ind = calculate_indicators(df2.copy(), cfg)
    assert generate_signal(df2_ind, cfg) == base_sig
