import math
import pytest

from bot.position import position_size


def test_position_size_basic_flooring():
    # entry=100, stop=95, per-unit risk=5; equity=2000, risk_pct=1% => risk_amount=20 => qty=4
    qty = position_size(entry=100, stop=95, equity=2000, risk_pct=0.01, step=0.1)
    assert math.isclose(qty, 4.0, rel_tol=1e-9)


def test_position_size_flooring_step():
    # raw qty ~ 4.37 -> step 0.5 => 4.0
    qty = position_size(entry=100, stop=95, equity=2185, risk_pct=0.01, step=0.5)
    assert math.isclose(qty, 4.0, rel_tol=1e-9)


def test_position_size_invalid_per_unit_risk():
    with pytest.raises(ValueError):
        position_size(entry=100, stop=100, equity=2000, risk_pct=0.01)


def test_position_size_positive_after_floor():
    # extremely small equity/risk but ensure floors above zero for step 0
    qty = position_size(entry=100, stop=99.9, equity=1, risk_pct=0.01)
    assert qty > 0

    # with step flooring causing zero should raise
    with pytest.raises(ValueError):
        position_size(entry=100, stop=99.9999, equity=0.1, risk_pct=0.0001, step=10)
