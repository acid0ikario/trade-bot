"""Position sizing utilities."""

from decimal import Decimal


def _floor_to_step(value: float, step: float) -> float:
    if step <= 0:
        return float(value)
    d = Decimal(str(value))
    s = Decimal(str(step))
    return float((d // s) * s)


def position_size(
    entry: float,
    stop: float,
    equity: float,
    risk_pct: float,
    step: float = 0.0,
) -> float:
    """Compute position size based on risk.

    Args:
        entry: Entry price.
        stop: Stop price.
        equity: Account equity in quote currency.
        risk_pct: Fraction of equity to risk per trade (e.g., 0.01 for 1%).
        step: Optional lot size step; if > 0, floor quantity to nearest multiple.

    Returns:
        Positive quantity sized so that (entry-stop)*qty ~= equity*risk_pct.

    Raises:
        ValueError: If per-unit risk is non-positive, or result floors to zero.
    """
    if risk_pct <= 0 or equity <= 0:
        raise ValueError("equity and risk_pct must be positive")
    per_unit_risk = abs(entry - stop)
    if per_unit_risk <= 0:
        raise ValueError("per-unit risk must be positive")

    risk_amount = equity * risk_pct
    raw_qty = risk_amount / per_unit_risk
    qty = _floor_to_step(raw_qty, step) if step and step > 0 else raw_qty
    if qty <= 0:
        raise ValueError("quantity must be positive after flooring")
    return float(qty)
