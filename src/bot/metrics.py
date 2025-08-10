"""Performance metrics for backtests."""
from typing import List, Sequence

from .paper import Trade


def sharpe(returns: Sequence[float], periods_per_year: float = 252.0, rf: float = 0.0) -> float:
    """Sharpe ratio from per-bar returns.

    - preserves sign (no abs/clamps)
    - annualizes by sqrt(periods_per_year)
    """
    try:
        import numpy as np
        r = np.asarray(list(returns), dtype=float)
        if r.size == 0:
            return 0.0
        # excess returns
        ex = r - float(rf) / float(periods_per_year)
        mu = ex.mean()
        # sample std (ddof=1); fallback to population if too short
        ddof = 1 if ex.size > 1 else 0
        std = ex.std(ddof=ddof)
        if std == 0 or not (std == std):  # NaN check
            return 0.0
        return float(mu / std * (float(periods_per_year) ** 0.5))
    except Exception:
        return 0.0


def cagr(equity: List[float], years: float) -> float:
    if not equity or years <= 0:
        return 0.0
    start = float(equity[0])
    end = float(equity[-1])
    if start <= 0:
        return 0.0
    return float((end / start) ** (1.0 / years) - 1.0)


def max_drawdown(equity: List[float]) -> float:
    if not equity:
        return 0.0
    peak = equity[0]
    max_dd = 0.0
    for x in equity:
        peak = max(peak, x)
        if peak > 0:
            dd = (x - peak) / peak
            if dd < max_dd:
                max_dd = dd
    # Return as negative fraction magnitude (absolute value as in prior behavior)
    return float(abs(max_dd))


def winrate(trades: List[Trade]) -> float:
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if (t.pnl or 0.0) > 0.0)
    return float(wins) / float(len(trades))


def profit_factor(trades: List[Trade]) -> float:
    """Gross profit / gross loss with robust edge cases.

    - No losses but some profit -> large finite PF (e.g., 1e9)
    - No profits and no losses -> NaN
    """
    if not trades:
        return 0.0
    profits = sum((t.pnl or 0.0) for t in trades if (t.pnl or 0.0) > 0.0)
    losses = -sum((t.pnl or 0.0) for t in trades if (t.pnl or 0.0) < 0.0)
    if losses == 0:
        if profits > 0:
            return 1e9
        return float("nan")
    return float(profits) / float(losses)


def expectancy(trades: List[Trade]) -> float:
    if not trades:
        return 0.0
    return float(sum((t.pnl or 0.0) for t in trades)) / float(len(trades))


def avg_trade(trades: List[Trade]) -> float:
    if not trades:
        return 0.0
    return float(
        sum(abs(t.pnl or 0.0) for t in trades) / float(len(trades))
    )
