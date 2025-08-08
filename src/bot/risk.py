"""Risk module (stub)."""

def compute_stop(entry: float, atr: float, k: float) -> float:
    return max(0.0, entry - atr * k)
