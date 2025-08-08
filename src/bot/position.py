"""Position sizing (stub)."""

def position_size(entry: float, stop: float, equity: float, risk_pct: float) -> float:
    risk_amount = equity * risk_pct
    per_unit = max(entry - stop, 1e-6)
    qty = risk_amount / per_unit
    return max(qty, 0.0)
