"""Strategy implementation for generating entry signals without lookahead bias.

This module exposes vectorized indicator helpers and a signal generator that operates
on the last CLOSED candle (i.e., ignores the potentially incomplete last row).
"""
from typing import Optional

import pandas as pd

from .config import AppConfig


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(series: pd.Series, period: int) -> pd.Series:
    """Compute Wilder's RSI using exponentially weighted means.

    This implementation is vectorized and matches Wilder smoothing by using
    an EWM alpha of 1/period. It returns a series aligned with the input.
    """
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    roll_up = up.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    roll_down = down.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = roll_up / roll_down
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def calculate_indicators(df: pd.DataFrame, cfg: AppConfig) -> pd.DataFrame:
    """Return a copy of df with precomputed indicator columns.

    Inputs
    - df: DataFrame with columns: open, high, low, close, volume. Timestamp column is optional.
    - cfg: AppConfig with parameters for EMA/RSI (and optional filters).

    Outputs
    - DataFrame including the following columns:
        - ema_fast, ema_slow, rsi
        - Optionally: adx (if cfg has enable_adx), vol_sma (if cfg has enable_vol_filter)

    Notes
    - All computations are vectorized; no Python loops.
    - Designed to be lookahead-safe when consumers only use the last CLOSED candle
      (index len(df)-2). This function computes across the whole series but does not
      require using the last potentially incomplete bar.
    """
    if df is None or df.empty:
        return df

    out = df.copy()
    close = out["close"].astype(float)
    out["ema_fast"] = _ema(close, cfg.ema_fast)
    out["ema_slow"] = _ema(close, cfg.ema_slow)
    out["rsi"] = _rsi(close, cfg.rsi_period)

    # Optional filters if exposed in config without changing existing behavior
    # ADX (Average Directional Index)
    if getattr(cfg, "enable_adx", False):
        high = out["high"].astype(float)
        low = out["low"].astype(float)
        close_shift = close.shift(1)
        tr = (high.combine(close_shift, lambda h, c: abs(h - c) if pd.notna(c) else 0.0))
        tr = tr.combine(low.combine(close_shift, lambda l, c: abs(l - c) if pd.notna(c) else 0.0), max)
        tr = tr.combine(high - low, max)
        period = int(getattr(cfg, "adx_period", 14))
        atr = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = up_move.mask((up_move <= down_move) | (up_move <= 0), 0.0)
        minus_dm = down_move.mask((down_move <= up_move) | (down_move <= 0), 0.0)
        plus_di = 100 * (plus_dm.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean() / atr)
        dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di)).fillna(0.0)
        out["adx"] = dx.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

    # Volume SMA filter
    if getattr(cfg, "enable_vol_filter", False):
        vol_period = int(getattr(cfg, "vol_sma_period", 20))
        out["vol_sma"] = out["volume"].astype(float).rolling(vol_period, min_periods=vol_period).mean()

    return out


def _trend_up(row: pd.Series) -> bool:
    """Return True when fast EMA is above slow EMA for the given row."""
    return float(row["ema_fast"]) > float(row["ema_slow"])


def _rsi_in_range(row: pd.Series, cfg: AppConfig) -> bool:
    """Return True when RSI is within [rsi_buy_min, rsi_buy_max] with a small tolerance."""
    rsi_val = float(row["rsi"]) if pd.notna(row.get("rsi", None)) else float("nan")
    rsi_margin = 3.0
    return (
        pd.notna(rsi_val)
        and rsi_val >= float(cfg.rsi_buy_min) - rsi_margin
        and rsi_val <= float(cfg.rsi_buy_max) + rsi_margin
    )


def _is_pullback(df: pd.DataFrame) -> bool:
    """Pullback confirmation using last CLOSED candle context.

    Returns True if the previous closed candle's close is lower than
    the close two candles ago. When called with a DataFrame that already
    excludes the most recent (incomplete) bar, this reduces to comparing
    df.iloc[-2] vs df.iloc[-1].
    """
    if df is None or len(df) < 2:
        return False
    return float(df.iloc[-2]["close"]) > float(df.iloc[-1]["close"])  # type: ignore[index]


def generate_signal(df: pd.DataFrame, cfg: AppConfig) -> Optional[str]:
    """Generate a long-entry signal based on last closed candle.

    Uses the last CLOSED candle by ignoring the final (potentially incomplete)
    row in df. Returns "buy" or None.
    """
    if df is None or len(df) < 2:
        return None

    # Ignore the last (potentially incomplete) bar to enforce no-lookahead
    view = df.iloc[:-1].copy()

    # Ensure enough history for indicators and pullback check (needs >= 2 bars)
    min_len = max(cfg.ema_slow, cfg.rsi_period) + 2
    if len(view) < min_len:
        return None

    # Use precomputed indicators when present; otherwise compute once here
    need_cols = {"ema_fast", "ema_slow", "rsi"}
    if not need_cols.issubset(view.columns):
        work = calculate_indicators(view, cfg)
    else:
        work = view

    i = len(work) - 1  # index of the last CLOSED candle within the sliced view

    pullback = _is_pullback(work)
    cond_trend = _trend_up(work.iloc[i])
    cond_momentum = _rsi_in_range(work.iloc[i], cfg)

    close_val = float(work.iloc[i]["close"])  # type: ignore[index]
    ema_fast_val = float(work.iloc[i]["ema_fast"])  # type: ignore[index]
    tol = (float(cfg.slippage_bps) / 10000.0) * abs(close_val)
    cond_close_above_fast = close_val + tol >= ema_fast_val

    if pullback and cond_trend and cond_momentum and cond_close_above_fast:
        return "buy"
    return None
