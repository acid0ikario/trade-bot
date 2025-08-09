"""Risk module providing stop calculations and daily loss guardrails."""

from typing import Iterable


def compute_stop(entry: float, atr: float, k: float) -> float:
    """ATR-based stop: max(0, entry - atr * k)."""
    return max(0.0, entry - atr * k)


def stop_by_swing_low(prices: Iterable[float], lookback: int = 20) -> float:
    """Return the lowest low over the last `lookback` prices.

    Args:
        prices: Sequence of historical low prices (recent first or last).
        lookback: Number of most recent values to consider.

    Raises:
        ValueError: If no prices provided or if the resulting stop is not positive.
    """
    arr = list(prices)
    if not arr:
        raise ValueError("prices must not be empty")
    look = max(1, min(len(arr), lookback))
    window = arr[-look:]
    stop = min(window)
    if stop <= 0:
        raise ValueError("computed stop must be positive")
    return float(stop)


def max_daily_loss_guard(pnl_list: Iterable[float], base_equity: float, max_loss_pct: float) -> bool:
    """Return True if trading can continue given daily PnL and loss cap.

    If cumulative PnL <= -base_equity * max_loss_pct, return False (halt new entries).
    Otherwise True.
    """
    cumulative = float(sum(pnl_list)) if pnl_list else 0.0
    allowed = -abs(base_equity) * abs(max_loss_pct)
    if cumulative <= allowed:
        return False
    return True


def kill_switch(pnl_list: Iterable[float], base_equity: float, max_loss_pct: float) -> bool:
    """Return True when trading should be halted due to daily loss breach.

    This is the logical inverse of `max_daily_loss_guard` and is convenient for
    the runner to decide whether to stop sending new orders for the day.
    """
    return not max_daily_loss_guard(pnl_list, base_equity, max_loss_pct)
