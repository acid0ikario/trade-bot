import pandas as pd
import numpy as np
import pytest

from bot.runner import run_paper
from bot.config import AppConfig, EnvVars
from bot.exchange import Exchange


class DummyExchange:
    def __init__(self, candles):
        self._candles = candles
        self.calls = 0

    def fetch_ohlcv(self, symbol, timeframe, limit=200):
        # Return last `limit` candles; each call advances by one to simulate time
        idx = min(self.calls, len(self._candles) - 1)
        self.calls += 1
        return self._candles[idx]


@pytest.fixture
def cfg_env():
    cfg = AppConfig(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        slippage_bps=0,
        fees=dict(maker=0.0, taker=0.0),
        risk_rr=2.0,
        ema_fast=3,
        ema_slow=5,
        rsi_period=3,
        rsi_buy_min=0,
        rsi_buy_max=100,
    )
    env = EnvVars(BASE_EQUITY=1000.0, MAX_DAILY_LOSS_PCT=0.5, RISK_PER_TRADE_PCT=0.1)
    return cfg, env


def make_candle(ts, o, h, l, c, v=1.0):
    return [ts, o, h, l, c, v]


def test_paper_trade_profit_and_equity_increase(monkeypatch, cfg_env):
    cfg, env = cfg_env

    # Build two snapshots of candles:
    # 1) Pre-entry history such that strategy returns "buy"
    base = [make_candle(i, 100 + i, 101 + i, 99 + i, 100 + i, 1.0) for i in range(200)]
    # Ensure pullback then breakout on last closed candle
    base[-3][4] = base[-4][4] + 1  # close[-3]
    base[-2][4] = base[-3][4] - 0.5  # close[-2] pullback
    base[-1][4] = base[-2][4] + 2  # current candle ignored by strategy

    # 2) Next snapshot where TP is hit on the next candle
    next_snap = base.copy()
    # simulate a big up move to hit TP
    next_snap[-1][2] = next_snap[-2][4] + 10  # high big jump

    candles_stream = [base, next_snap, next_snap]

    dummy = DummyExchange(candles_stream)
    monkeypatch.setattr("bot.runner.Exchange", lambda cfg, env: dummy)

    broker = run_paper(cfg, env, max_iterations=2, sleep_seconds=0)
    assert len(broker.trade_log) == 1
    assert broker.trade_log[0].pnl is not None
    assert broker.equity > env.BASE_EQUITY


def test_loss_guard(monkeypatch, cfg_env):
    cfg, env = cfg_env

    # Build candles that open a trade, then force a stop hit causing large loss
    base = [make_candle(i, 100 + i, 101 + i, 99 + i, 100 + i, 1.0) for i in range(200)]
    base[-3][4] = base[-4][4] + 1
    base[-2][4] = base[-3][4] - 0.5

    next_snap = base.copy()
    next_snap[-1][3] = next_snap[-2][4] - 50  # low pierces far below entry -> stop

    candles_stream = [base, next_snap]

    dummy = DummyExchange(candles_stream)
    monkeypatch.setattr("bot.runner.Exchange", lambda cfg, env: dummy)

    # Set a small max daily loss pct so kill switch triggers after loss
    env.MAX_DAILY_LOSS_PCT = 0.0001
    broker = run_paper(cfg, env, max_iterations=2, sleep_seconds=0)
    assert len(broker.trade_log) == 1
    assert broker.trade_log[0].pnl is not None
    # Should halt due to loss guard
    assert broker.equity <= env.BASE_EQUITY
