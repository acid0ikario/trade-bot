import pytest

from bot.risk import compute_stop, stop_by_swing_low, max_daily_loss_guard, kill_switch


def test_compute_stop_basic():
    assert compute_stop(100, 2, 1.5) == 100 - 2 * 1.5
    assert compute_stop(1.0, 5.0, 1.0) == 0.0  # never negative


def test_stop_by_swing_low():
    lows = [101, 99, 100, 98, 97, 102]
    assert stop_by_swing_low(lows, lookback=3) == min(lows[-3:])
    assert stop_by_swing_low(lows, lookback=10) == min(lows)
    with pytest.raises(ValueError):
        stop_by_swing_low([], lookback=5)


def test_max_daily_loss_guard_and_kill_switch():
    base_equity = 2000
    max_loss_pct = 0.03  # $60

    # within limit (loss less than 60)
    pnl_list = [-10, -20, +5]
    assert max_daily_loss_guard(pnl_list, base_equity, max_loss_pct) is True
    assert kill_switch(pnl_list, base_equity, max_loss_pct) is False

    # breach limit (loss >= 60)
    pnl_list = [-30, -40]
    assert max_daily_loss_guard(pnl_list, base_equity, max_loss_pct) is False
    assert kill_switch(pnl_list, base_equity, max_loss_pct) is True
