import math

from bot.metrics import cagr, max_drawdown, winrate, profit_factor, expectancy, avg_trade
from bot.paper import Trade
from bot.backtest import run_backtest
from bot.config import AppConfig


def test_metrics_simple():
    # CAGR doubling in 1 year ~ 100%
    eq = [100, 200]
    assert math.isclose(cagr(eq, 1), 1.0, rel_tol=1e-6)
    # Max drawdown on monotonic up is 0
    assert max_drawdown([1, 2, 3, 4]) == 0.0

    # Trades: two wins of 10, one loss of -5
    trades = [
        Trade(symbol="X", side="buy", entry_price=1, stop_price=0, take_profit=0, qty=1, entry_time=None, exit_price=0, exit_time=None, pnl=10),
        Trade(symbol="X", side="buy", entry_price=1, stop_price=0, take_profit=0, qty=1, entry_time=None, exit_price=0, exit_time=None, pnl=10),
        Trade(symbol="X", side="buy", entry_price=1, stop_price=0, take_profit=0, qty=1, entry_time=None, exit_price=0, exit_time=None, pnl=-5),
    ]
    assert math.isclose(winrate(trades), 2/3, rel_tol=1e-6)
    assert math.isclose(profit_factor(trades), (10+10)/5, rel_tol=1e-6)
    assert math.isclose(expectancy(trades), (10+10-5)/3, rel_tol=1e-6)
    assert math.isclose(avg_trade(trades), (10+10+5)/3, rel_tol=1e-6)


def test_backtest_runs_minimal_grid():
    # Minimal data loader returning small deterministic dataset
    def loader(symbol, timeframe, years):
        data = []
        for i in range(220):
            # timestamp, open, high, low, close, volume
            data.append([i, 100+i*0.1, 100+i*0.1+1, 100+i*0.1-1, 100+i*0.1, 1])
        import pandas as pd
        return pd.DataFrame(data, columns=["timestamp","open","high","low","close","volume"])

    cfg = AppConfig()
    grid = {"ema_fast":[3], "ema_slow":[5], "rsi_period":[3], "rsi_buy_min":[0], "rsi_buy_max":[100]}
    res = run_backtest("BTC/USDT", "1h", 1, cfg, grid, data_loader=loader)
    assert isinstance(res, list) and len(res) == 1
    item = res[0]
    assert "cagr" in item and "max_dd" in item and "equity" in item
    assert isinstance(item["equity"], list) and len(item["equity"]) > 0
