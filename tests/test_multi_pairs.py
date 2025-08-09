import pandas as pd
import numpy as np
import pytest

from bot.runner import run_paper
from bot.config import AppConfig, EnvVars


def gen_series(n=200, rho=0.95, seed=0):
    rng = np.random.default_rng(seed)
    eps1 = rng.normal(0, 1, n)
    eps2 = rng.normal(0, 1, n)
    z1 = eps1
    z2 = rho * eps1 + np.sqrt(1 - rho**2) * eps2
    # Build prices as cumulative sum to simulate trends
    p1 = 100 + np.cumsum(z1 * 0.1)
    p2 = 100 + np.cumsum(z2 * 0.1)
    return p1, p2


class DummyExchange:
    def __init__(self, data_map):
        self.data_map = data_map

    def fetch_ohlcv(self, symbol, timeframe, limit=200):
        arr = self.data_map[symbol]
        # ccxt style
        return [[i, o, h, l, c, v] for i, (o, h, l, c, v) in enumerate(arr)][-limit:]


def make_df_from_close(close):
    close = np.asarray(close, dtype=float)
    n = len(close)
    open_ = close + 0.01
    high = np.maximum(open_, close) + 0.02
    low = np.minimum(open_, close) - 0.02
    vol = np.ones(n)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": vol})


def build_data_map():
    n = 250
    p_btc, p_eth = gen_series(n=n, rho=0.95, seed=42)
    p_bnb = 100 + np.cumsum(np.random.default_rng(7).normal(0, 1, n) * 0.1)  # less correlated

    df_btc = make_df_from_close(p_btc)
    df_eth = make_df_from_close(p_eth)
    df_bnb = make_df_from_close(p_bnb)

    def to_ohlcv(df):
        return list(zip(df.open, df.high, df.low, df.close, df.volume))

    return {
        "BTC/USDT": to_ohlcv(df_btc),
        "ETH/USDT": to_ohlcv(df_eth),
        "BNB/USDT": to_ohlcv(df_bnb),
    }


@pytest.fixture
def cfg_env():
    cfg = AppConfig(
        symbols_whitelist=["BTC/USDT", "ETH/USDT", "BNB/USDT"],
        timeframe="1h",
        slippage_bps=0,
        fees=dict(maker=0.0, taker=0.0),
        risk_rr=2.0,
        ema_fast=5,
        ema_slow=10,
        rsi_period=5,
        rsi_buy_min=0,
        rsi_buy_max=100,
        max_notional_usdt_per_pair=50,
        max_correlated_trades=1,
        correlation_threshold=0.85,
        max_open_trades=3,
    )
    env = EnvVars(BASE_EQUITY=1000.0, MAX_DAILY_LOSS_PCT=0.5, RISK_PER_TRADE_PCT=0.1)
    return cfg, env


def test_correlation_guard_blocks_over_cap(monkeypatch, cfg_env):
    cfg, env = cfg_env
    data_map = build_data_map()
    dummy = DummyExchange(data_map)
    monkeypatch.setattr("bot.runner.Exchange", lambda cfg, env: dummy)

    broker = run_paper(cfg, env, max_iterations=1)

    # With high correlation (BTC ~ ETH) and max_correlated_trades=1,
    # expect at most 1 of (BTC, ETH) to be opened; BNB can be opened as uncorrelated
    opened = set(broker.open_positions.keys())
    assert len(opened.intersection({"BTC/USDT", "ETH/USDT"})) <= 1
    # Allow up to max_open_trades, but per our synthetic data, at least BNB should be eligible
    assert len(opened) <= cfg.max_open_trades


def test_per_pair_caps_enforced(monkeypatch, cfg_env):
    cfg, env = cfg_env
    data_map = build_data_map()
    dummy = DummyExchange(data_map)
    monkeypatch.setattr("bot.runner.Exchange", lambda cfg, env: dummy)

    # Tight per-pair cap so that position size is reduced below raw risk-based sizing
    cfg.max_notional_usdt_per_pair = 20

    broker = run_paper(cfg, env, max_iterations=1)

    for sym, t in broker.open_positions.items():
        assert t.entry_price * t.qty <= cfg.max_notional_usdt_per_pair + 1e-6
