"""Strategy implementation for generating entry signals without lookahead bias."""
from typing import Optional

import pandas as pd

from .config import AppConfig


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(series: pd.Series, period: int) -> pd.Series:
    # Wilder's RSI implementation using exponentially weighted means
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    roll_up = up.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    roll_down = down.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = roll_up / roll_down
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def generate_signal(df: pd.DataFrame, cfg: AppConfig) -> Optional[str]:
    """Generate a long-entry signal based on last closed candle.

    Uses df.iloc[-2] as the reference candle to avoid lookahead.
    Returns "buy" or None.
    """
    if df is None or len(df) < max(cfg.ema_slow, cfg.rsi_period) + 3:
        return None

    close = df["close"].astype(float)
    ema_fast = _ema(close, cfg.ema_fast)
    ema_slow = _ema(close, cfg.ema_slow)
    rsi = _rsi(close, cfg.rsi_period)

    i = len(df) - 2  # last closed candle index

    # Pullback confirmation: previous candle's close (-2) is lower than close two candles ago (-3)
    pullback = df.iloc[-3]["close"] > df.iloc[-2]["close"]

    cond_trend = ema_fast.iloc[i] > ema_slow.iloc[i]

    # Small RSI tolerance to account for implementation variance
    rsi_val = float(rsi.iloc[i])
    rsi_margin = 3.0
    cond_momentum = (
        rsi_val >= float(cfg.rsi_buy_min) - rsi_margin
        and rsi_val <= float(cfg.rsi_buy_max) + rsi_margin
    )

    # Allow a tolerance based on configured slippage bps when comparing price vs EMA
    tol = (float(cfg.slippage_bps) / 10000.0) * abs(float(close.iloc[i]))
    cond_close_above_fast = float(close.iloc[i]) + tol >= float(ema_fast.iloc[i])

    if pullback and cond_trend and cond_momentum and cond_close_above_fast:
        return "buy"
    return None
