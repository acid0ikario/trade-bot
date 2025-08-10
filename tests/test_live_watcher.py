import time
import pytest

from bot.runner import watch_open_orders


class StubLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []

    def info(self, msg):
        self.infos.append(str(msg))

    def warning(self, msg):
        self.warnings.append(str(msg))


class FakeExchange:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        # Two open orders representing OCO legs
        self._open = [
            {"id": "tp1", "type": "limit", "side": "sell", "price": 110.0},
            {"id": "sl1", "type": "stop_loss_limit", "side": "sell", "price": 90.0},
        ]
        self._closed = []
        self.canceled = []

    def fetch_open_orders(self, symbol):
        # return a shallow copy to simulate fresh fetch
        return list(self._open)

    def fetch_closed_orders(self, symbol):
        return list(self._closed)

    def cancel_order(self, order_id, symbol):
        self.canceled.append(order_id)
        # remove from open orders if present
        self._open = [o for o in self._open if str(o.get("id")) != str(order_id)]
        return {"id": order_id, "status": "canceled"}


@pytest.mark.parametrize("filled_id, expect_cancel", [("tp1", "sl1"), ("sl1", "tp1")])
def test_watcher_cancels_opposite_on_fill(filled_id, expect_cancel):
    ex = FakeExchange(dry_run=False)
    # Mark one leg as filled
    filled_order = next(o for o in ex._open if o["id"] == filled_id)
    ex._closed = [{**filled_order, "status": "filled"}]

    logger = StubLogger()

    th = watch_open_orders(ex, symbol="BTC/USDT", poll_sec=0.01, logger=logger)
    th.join(timeout=1.5)

    assert not th.is_alive(), "watcher thread did not finish"
    assert ex.canceled == [expect_cancel]


def test_watcher_idempotent_does_not_recancel():
    ex = FakeExchange(dry_run=False)
    # Keep open orders intact to force multiple polls
    filled_order = next(o for o in ex._open if o["id"] == "tp1")
    ex._closed = [{**filled_order, "status": "closed"}]

    # Override cancel to not remove open order, so the watcher loops a few times
    def cancel_no_remove(order_id, symbol):
        ex.canceled.append(order_id)
        return {"id": order_id, "status": "canceled"}

    ex.cancel_order = cancel_no_remove  # type: ignore

    logger = StubLogger()
    th = watch_open_orders(ex, symbol="BTC/USDT", poll_sec=0.01, logger=logger)
    th.join(timeout=1.5)

    assert not th.is_alive(), "watcher thread did not finish"
    # Should cancel exactly once despite repeated polls
    assert ex.canceled == ["sl1"]


def test_watcher_dry_run_logs_only():
    ex = FakeExchange(dry_run=True)
    # Simulate TP filled
    filled_order = next(o for o in ex._open if o["id"] == "tp1")
    ex._closed = [{**filled_order, "status": "filled"}]

    logger = StubLogger()
    th = watch_open_orders(ex, symbol="BTC/USDT", poll_sec=0.01, logger=logger)
    th.join(timeout=1.5)

    assert not th.is_alive(), "watcher thread did not finish"
    # No cancellations should be executed in dry-run
    assert ex.canceled == []
    # There should be at least one dry-run log line
    assert any("DRY-RUN" in m for m in logger.infos)
