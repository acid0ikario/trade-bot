"""Metrics (stub)."""

def sharpe(returns, rf=0.0):
    try:
        import numpy as np
        if len(returns) == 0:
            return 0.0
        r = np.asarray(returns)
        if r.std() == 0:
            return 0.0
        return (r.mean() - rf) / r.std() * (252 ** 0.5)
    except Exception:
        return 0.0
