import pytest

from bot.runner import run_live
from bot.config import AppConfig, EnvVars


class DummyExchange:
    def __init__(self):
        self.buys = []
        self.ocos = []
        self._price = 100.0
        self._candles = [[i, 99, 101, 98, 100, 1.0] for i in range(200)]
        # Make a pullback and signal on the last closed candle
        self._candles[-3][4] = 101
        self._candles[-2][4] = 100
        self._candles[-1][4] = 102

    def fetch_ohlcv(self, symbol, timeframe, limit=200):
        return self._candles

    def get_balance(self, quote):
        return 1000.0

    def create_market_buy(self, symbol, qty):
        self.buys.append((symbol, qty))
        return {"id": "buy1"}

    def place_oco_takeprofit_stoploss(self, symbol, qty, tp, sl):
        self.ocos.append((symbol, qty, tp, sl))
        return {"tp_order_id": "tp1", "sl_order_id": "sl1"}


@pytest.fixture
def cfg_env():
    cfg = AppConfig(
        symbols_whitelist=["BTC/USDT"],
        timeframe="1h",
        slippage_bps=100,  # allow tolerance for close vs EMA
        fees=dict(maker=0.0, taker=0.0),
        risk_rr=2.0,
        ema_fast=3,
        ema_slow=5,
        rsi_period=3,
        rsi_buy_min=0,
        rsi_buy_max=100,
        max_notional_per_trade_usdt=10000,
    )
    env = EnvVars(BASE_EQUITY=1000.0, MAX_DAILY_LOSS_PCT=0.5, RISK_PER_TRADE_PCT=0.1)
    return cfg, env


def test_live_dry_run(monkeypatch, cfg_env):
    cfg, env = cfg_env
    dummy = DummyExchange()
    monkeypatch.setattr("bot.runner.Exchange", lambda cfg, env: dummy)

    # Dry-run should not place orders
    run_live(cfg, env, dry_run=True, max_iterations=1)
    assert len(dummy.buys) == 0
    assert len(dummy.ocos) == 0


def test_live_places_orders(monkeypatch, cfg_env):
    cfg, env = cfg_env
    dummy = DummyExchange()
    monkeypatch.setattr("bot.runner.Exchange", lambda cfg, env: dummy)

    run_live(cfg, env, dry_run=False, max_iterations=1)
    assert len(dummy.buys) == 1
    assert len(dummy.ocos) == 1


def test_kill_switch_blocks_orders(monkeypatch, cfg_env):
    cfg, env = cfg_env
    dummy = DummyExchange()
    monkeypatch.setattr("bot.runner.Exchange", lambda cfg, env: dummy)

    # Set max daily loss pct to zero to trigger kill switch immediately
    env.MAX_DAILY_LOSS_PCT = 0.0
    run_live(cfg, env, dry_run=False, max_iterations=1)
    assert len(dummy.buys) == 0
    assert len(dummy.ocos) == 0
