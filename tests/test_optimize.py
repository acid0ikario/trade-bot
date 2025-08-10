import io
from pathlib import Path
import pandas as pd
import yaml

from bot.optimize import _top_quartile, _recommend_defaults, optimize_from_csv, run_ab
from bot.config import AppConfig


def test_top_quartile_and_recommendations(tmp_path: Path):
    # Build a tiny CSV in-memory
    df = pd.DataFrame(
        [
            {"ema_fast": 10, "ema_slow": 20, "rsi_period": 14, "rsi_buy_min": 40, "rsi_buy_max": 60, "atr_k": 1.5, "risk_rr": 2.0, "sharpe": 1.0, "max_dd": -0.1},
            {"ema_fast": 12, "ema_slow": 24, "rsi_period": 14, "rsi_buy_min": 45, "rsi_buy_max": 60, "atr_k": 1.2, "risk_rr": 2.2, "sharpe": 2.0, "max_dd": -0.05},
            {"ema_fast": 8,  "ema_slow": 16, "rsi_period": 14, "rsi_buy_min": 35, "rsi_buy_max": 55, "atr_k": 1.8, "risk_rr": 1.8, "sharpe": 0.5, "max_dd": -0.2},
            {"ema_fast": 11, "ema_slow": 22, "rsi_period": 14, "rsi_buy_min": 42, "rsi_buy_max": 58, "atr_k": 1.4, "risk_rr": 2.1, "sharpe": 1.8, "max_dd": -0.08},
        ]
    )
    csv_path = tmp_path / "results.csv"
    df.to_csv(csv_path, index=False)

    out_yaml = tmp_path / "optimized_defaults.yaml"
    rec = optimize_from_csv(csv_path, out_yaml)

    # Should have keys present
    assert set(["ema_fast", "ema_slow", "rsi_period", "rsi_buy_min", "rsi_buy_max", "atr_k", "risk_rr"]).issubset(set(rec.keys()))
    # YAML file exists
    assert out_yaml.exists()
    y = yaml.safe_load(out_yaml.read_text())
    assert isinstance(y, dict)


def test_ab_outputs(tmp_path: Path, monkeypatch):
    # Mock run_backtest inside optimize.run_ab to return deterministic metrics
    from bot import optimize as opt

    def fake_run_backtest(symbol, timeframe, years, cfg, param_grid, data_loader=None):
        # return list with one result dict carrying metrics only
        base = 1.0 + (1.0 if getattr(cfg, "enable_adx", False) else 0.0) + (0.5 if getattr(cfg, "enable_vol_filter", False) else 0.0)
        return [{"sharpe": base, "max_dd": -0.1 + 0.01 * base, "winrate": 0.5 + 0.1 * base, "pf": 1.5 + 0.2 * base, "expectancy": 0.01 * base, "cagr": 0.1 * base}]

    monkeypatch.setattr(opt, "run_backtest", fake_run_backtest)

    cfg = AppConfig()
    df = opt.run_ab("BTC/USDT", "1h", 1, cfg)

    # Expect four variants
    assert set(df["variant"]) == {"baseline", "adx_only", "vol_only", "both"}

    # Save and verify outputs
    out_csv = tmp_path / "ab_results.csv"
    out_summary = tmp_path / "ab_summary.txt"
    opt.save_ab_results(df, out_csv, out_summary)

    assert out_csv.exists()
    out = pd.read_csv(out_csv)
    assert set(["variant", "sharpe", "max_dd", "winrate", "pf", "expectancy", "cagr"]).issubset(set(out.columns))
    assert out_summary.exists()
    txt = out_summary.read_text()
    assert "A/B Backtest Summary" in txt
