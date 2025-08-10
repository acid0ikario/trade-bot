"""Backtesting engine with simple grid search and artifact outputs."""

import argparse
import itertools
from pathlib import Path
import hashlib
import time

import pandas as pd

from .config import AppConfig
from .strategy import generate_signal
from .position import position_size
from .risk import compute_stop, max_daily_loss_guard, kill_switch
from .paper import PaperBroker
from .metrics import cagr, max_drawdown, winrate, profit_factor, expectancy, avg_trade, sharpe


def _hash_params(params: dict) -> str:
    items = sorted(params.items())
    s = "|".join(f"{k}={v}" for k, v in items)
    return hashlib.md5(s.encode()).hexdigest()[:8]


def _default_loader(symbol: str, timeframe: str, years: int):
    # Placeholder: generate synthetic walk for tests; real impl would use ccxt
    import numpy as np
    n = max(200, years * 365 * 24)
    ts = pd.date_range("2020-01-01", periods=n, freq=timeframe)
    prices = 100 + np.cumsum(np.random.randn(n))
    df = pd.DataFrame({
        "timestamp": ts.astype(int) // 10**9,
        "open": prices,
        "high": prices + 1,
        "low": prices - 1,
        "close": prices,
        "volume": 1.0,
    })
    return df


def run_backtest(symbol: str, timeframe: str, years: int, cfg: AppConfig, param_grid: dict, data_loader=None):
    data_loader = data_loader or _default_loader
    base_df = data_loader(symbol, timeframe, years)

    # Build parameter combinations
    keys = list(param_grid.keys())
    combos = list(itertools.product(*[param_grid[k] for k in keys]))
    results = []

    artifacts_dir = Path("data/artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    csv_path = artifacts_dir / "backtest_results.csv"

    # CSV hygiene and run metadata
    MIN_TRADES = int(getattr(cfg, "min_trades", 30))
    run_id = int(time.time())

    # Map timeframe to bars per year for Sharpe
    tf_map = {
        "1m": 365 * 24 * 60,
        "5m": 365 * 24 * 12,
        "15m": 365 * 24 * 4,
        "1h": 365 * 24,
        "4h": 365 * 6,
        "1d": 365,
    }
    periods_per_year = float(tf_map.get(timeframe, 365 * 24))

    for combo in combos:
        params = dict(zip(keys, combo))
        # Override cfg by creating a shallow copy
        cfg_copy = cfg.copy()
        for k, v in params.items():
            setattr(cfg_copy, k, v)

        broker = PaperBroker(cfg_copy, equity=1000.0)
        equity_curve = [broker.equity]

        df = base_df.copy().reset_index(drop=True)
        for i in range(200, len(df)):
            window = df.iloc[: i + 1]
            sig = generate_signal(window[["open", "high", "low", "close", "volume"]], cfg_copy)
            if sig == "buy" and cfg.symbol not in broker.open_positions:
                entry = float(window.iloc[-2]["close"])  # last closed
                stop = compute_stop(entry, atr=entry * 0.0 + 1.0, k=cfg_copy.atr_k)
                rr = float(cfg_copy.risk_rr)
                tp = entry + (entry - stop) * rr
                try:
                    qty = position_size(entry, stop, broker.equity, 0.01, step=0.0)
                except Exception:
                    qty = 0.0
                if qty > 0:
                    broker.buy(symbol, entry, qty, stop, tp)

            # Update with current last candle
            broker.update_prices(window.tail(1))
            equity_curve.append(broker.equity)

            realized = [t.pnl for t in broker.trade_log if t.pnl is not None]
            if kill_switch(realized, 1000.0, 0.2):
                break

        tr = broker.trade_log
        n_trades = len(tr)
        returns = pd.Series(equity_curve).pct_change().dropna().values
        metrics = {
            "cagr": cagr(equity_curve, max(1, years)),
            "max_dd": max_drawdown(equity_curve),
            "winrate": winrate(tr),
            "pf": profit_factor(tr),
            "expectancy": expectancy(tr),
            "avg_trade": avg_trade(tr),
            "sharpe": sharpe(returns, periods_per_year=periods_per_year),
            "n_trades": n_trades,
        }
        rec = {**params, **metrics, "equity": equity_curve, "run_id": run_id}
        results.append(rec)

        # Append CSV row
        valid_row = n_trades >= MIN_TRADES
        row = {**params, **metrics, "valid_row": valid_row, "run_id": run_id}
        header = not csv_path.exists()
        import csv

        with csv_path.open("a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(row.keys()))
            if header:
                w.writeheader()
            w.writerow(row)

        # Save equity plot
        try:
            import matplotlib.pyplot as plt
            import numpy as np

            plt.figure(figsize=(6, 3))
            plt.plot(equity_curve)
            plt.title("Equity Curve")
            plt.tight_layout()
            plot_path = artifacts_dir / f"equity_{_hash_params(params)}.png"
            plt.savefig(plot_path)
            plt.close()
        except Exception:
            pass

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--years", type=int, default=1)
    parser.add_argument("--grid", type=str, default="")
    args = parser.parse_args()

    cfg = AppConfig()
    if args.grid:
        import yaml
        with open(args.grid, "r", encoding="utf-8") as f:
            grid = yaml.safe_load(f)
    else:
        grid = {"ema_fast": [10], "ema_slow": [20], "rsi_period": [14], "rsi_buy_min": [45], "rsi_buy_max": [60]}

    run_backtest(args.symbol, args.timeframe, args.years, cfg, grid)


if __name__ == "__main__":
    main()
