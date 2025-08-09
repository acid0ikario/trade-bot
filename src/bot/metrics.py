"""Performance metrics for backtests."""
from typing import List

from .paper import Trade


def sharpe(returns, rf=0.0):
    try:
        import numpy as np
        if len(returns) == 0:
            return 0.0
        r = np.asarray(returns, dtype=float)
        std = r.std()
        if std == 0 or not (std == std):  # NaN check
            return 0.0
        return float((r.mean() - rf) / std * (252 ** 0.5))
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
    return float(abs(max_dd))


def winrate(trades: List[Trade]) -> float:
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if (t.pnl or 0.0) > 0.0)
    return float(wins) / float(len(trades))


def profit_factor(trades: List[Trade]) -> float:
    if not trades:
        return 0.0
    profits = sum((t.pnl or 0.0) for t in trades if (t.pnl or 0.0) > 0.0)
    losses = -sum((t.pnl or 0.0) for t in trades if (t.pnl or 0.0) < 0.0)
    if losses == 0:
        return float(profits > 0) * float('inf') if profits > 0 else 0.0
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
