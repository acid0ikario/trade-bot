import pandas as pd
import numpy as np

from bot.strategy import generate_signal
from bot.config import AppConfig


def make_df(prices):
    n = len(prices)
    return pd.DataFrame(
        {
            "open": prices,
            "high": prices,
            "low": prices,
            "close": prices,
            "volume": np.ones(n),
        }
    )


def test_no_lookahead_and_positive_signal():
    cfg = AppConfig(
        ema_fast=3,
        ema_slow=5,
        rsi_period=3,
        rsi_buy_min=45,
        rsi_buy_max=60,
    )
    # Construct prices so that on the last closed candle:
    # - EMAfast > EMAslow
    # - RSI in range
    # - close > EMAfast
    # - pullback: prev close < close two candles ago
    prices = [100, 101, 102, 101, 103, 104, 103, 105]
    df = make_df(prices)

    sig = generate_signal(df, cfg)
    assert sig == "buy"

    # Modify the last (incomplete) candle; signal should not change
    df.iloc[-1, df.columns.get_loc("close")] = 10.0
    sig2 = generate_signal(df, cfg)
    assert sig2 == "buy"


def test_negative_cases():
    cfg = AppConfig(ema_fast=3, ema_slow=5, rsi_period=3, rsi_buy_min=45, rsi_buy_max=60)

    # Not enough data
    df_short = make_df([100, 101, 102])
    assert generate_signal(df_short, cfg) is None

    # Fail trend: EMAfast <= EMAslow
    prices = [100, 100, 100, 100, 100, 100, 100, 100]
    df = make_df(prices)
    assert generate_signal(df, cfg) is None

    # Fail momentum: RSI out of range (strong uptrend RSI > 60)
    prices = [100, 101, 102, 103, 104, 105, 106, 107]
    df = make_df(prices)
    assert generate_signal(df, cfg) is None

    # Fail close above fast
    prices = [100, 101, 100.5, 101, 100.8, 100.7, 100.6, 100.5]
    df = make_df(prices)
    assert generate_signal(df, cfg) is None

    # Fail pullback condition: prev close not lower than two candles ago
    prices = [100, 101, 102, 103, 104, 104.5, 105, 105.5]
    df = make_df(prices)
    assert generate_signal(df, cfg) is None
