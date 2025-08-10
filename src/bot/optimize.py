"""Parameter optimizer and A/B backtest comparisons.

CLI:
  python -m bot.optimize --results data/artifacts/backtest_results.csv
  python -m bot.optimize --ab
"""
from __future__ import annotations

import argparse
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Tuple

import pandas as pd
import yaml

from .config import AppConfig
from .backtest import run_backtest


PARAM_KEYS = [
    "ema_fast",
    "ema_slow",
    "rsi_period",
    "rsi_buy_min",
    "rsi_buy_max",
    "atr_k",
    "risk_rr",
]


def _top_quartile(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    # Rank by Sharpe desc, then MaxDD desc (less negative is better)
    df = df.copy()
    # Convert columns to float where possible
    for col in ["sharpe", "max_dd", "pf", "cagr", "n_trades"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["sharpe", "max_dd"])  # require both
    if df.empty:
        return df
    sharpe_q75 = df["sharpe"].quantile(0.75)
    top = df[df["sharpe"] >= sharpe_q75].copy()
    # Break ties by higher max_dd (less negative)
    top = top.sort_values(["sharpe", "max_dd"], ascending=[False, False])
    return top


def _mode_or_median(series: pd.Series) -> Any:
    # If mostly integer-like, return median rounded; else median
    s = series.dropna()
    if s.empty:
        return None
    if pd.api.types.is_integer_dtype(s) or pd.api.types.is_float_dtype(s):
        return float(median(list(map(float, s))))
    # Fallback: first value
    return s.iloc[0]


def _recommend_defaults(df: pd.DataFrame) -> Dict[str, Any]:
    rec: Dict[str, Any] = {}
    for k in PARAM_KEYS:
        if k in df.columns:
            val = _mode_or_median(df[k])
            if val is not None:
                # ints where expected
                if k in ("ema_fast", "ema_slow", "rsi_period", "rsi_buy_min", "rsi_buy_max"):
                    rec[k] = int(round(float(val)))
                else:
                    rec[k] = float(val)
    return rec


def write_yaml(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=True)


def optimize_from_csv(csv_path: Path, out_path: Path, *, pf_min: float = 1.0, cagr_min: float = 0.0, max_dd_max: float = 0.40, ntrades_min: int = 50) -> Dict[str, Any]:
    df = pd.read_csv(csv_path)
    # Apply constraints
    for col in ["pf", "cagr", "max_dd", "n_trades", "sharpe"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    filt = (
        (df.get("pf", 0) > pf_min)
        & (df.get("cagr", 0) > cagr_min)
        & (df.get("max_dd", 1) <= max_dd_max)
        & (df.get("n_trades", 0) >= ntrades_min)
    )
    df2 = df[filt].copy()
    top = _top_quartile(df2)
    recs = _recommend_defaults(top)
    write_yaml(out_path, recs)
    return recs


def _ab_variants() -> List[Tuple[str, Dict[str, Any]]]:
    return [
        ("baseline", {"enable_adx": False, "enable_vol_filter": False}),
        ("adx_only", {"enable_adx": True, "enable_vol_filter": False}),
        ("vol_only", {"enable_adx": False, "enable_vol_filter": True}),
        ("both", {"enable_adx": True, "enable_vol_filter": True}),
    ]


def _collect_metrics(results: List[Dict[str, Any]]) -> Dict[str, float]:
    # Aggregate useful metrics from a single backtest run (use last record)
    if not results:
        return {"sharpe": 0.0, "max_dd": 0.0, "winrate": 0.0, "pf": 0.0, "expectancy": 0.0, "cagr": 0.0, "n_trades": 0}
    r = results[-1]
    return {
        "sharpe": float(r.get("sharpe", 0.0)),
        "max_dd": float(r.get("max_dd", 0.0)),
        "winrate": float(r.get("winrate", 0.0)),
        "pf": float(r.get("pf", 0.0)),
        "expectancy": float(r.get("expectancy", 0.0)),
        "cagr": float(r.get("cagr", 0.0)),
        "n_trades": int(r.get("n_trades", 0)),
    }


def run_ab(symbol: str, timeframe: str, years: int, cfg: AppConfig, data_loader=None) -> pd.DataFrame:
    rows = []
    for name, flags in _ab_variants():
        cfg_copy = cfg.copy()
        for k, v in flags.items():
            setattr(cfg_copy, k, v)
        # ensure thresholds available
        if not hasattr(cfg_copy, "adx_threshold"):
            setattr(cfg_copy, "adx_threshold", 20.0)
        if not hasattr(cfg_copy, "vol_sma_period"):
            setattr(cfg_copy, "vol_sma_period", 20)
        if not hasattr(cfg_copy, "volume_factor"):
            setattr(cfg_copy, "volume_factor", 1.5)
        results = run_backtest(
            symbol,
            timeframe,
            years,
            cfg_copy,
            {"ema_fast": [cfg_copy.ema_fast], "ema_slow": [cfg_copy.ema_slow], "rsi_period": [cfg_copy.rsi_period], "rsi_buy_min": [cfg_copy.rsi_buy_min], "rsi_buy_max": [cfg_copy.rsi_buy_max]},
            data_loader=data_loader,
        )
        m = _collect_metrics(results)
        rows.append({"variant": name, **m})
    return pd.DataFrame(rows)


def save_ab_results(df: pd.DataFrame, out_csv: Path, out_summary: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    # Simple summary
    best = df.sort_values(["sharpe", "max_dd"], ascending=[False, False]).iloc[0]
    lines = [
        "A/B Backtest Summary:",
        df.to_string(index=False),
        "",
        f"Best variant: {best['variant']} (Sharpe={best['sharpe']:.3f}, MaxDD={best['max_dd']:.3f}, n_trades={int(best['n_trades'])})",
    ]
    out_summary.write_text("\n".join(lines), encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--results", type=str, default="")
    p.add_argument("--ab", action="store_true")
    p.add_argument("--symbol", type=str, default="BTC/USDT")
    p.add_argument("--timeframe", type=str, default="1h")
    p.add_argument("--years", type=int, default=1)
    # Optimizer constraints
    p.add_argument("--pf-min", type=float, default=1.0)
    p.add_argument("--cagr-min", type=float, default=0.0)
    p.add_argument("--max-dd-max", type=float, default=0.40)
    p.add_argument("--ntrades-min", type=int, default=50)
    args = p.parse_args()

    artifacts = Path("data/artifacts")
    artifacts.mkdir(parents=True, exist_ok=True)

    cfg = AppConfig()

    if args.results:
        csv_path = Path(args.results)
        out = artifacts / "optimized_defaults.yaml"
        rec = optimize_from_csv(csv_path, out, pf_min=args.pf_min, cagr_min=args.cagr_min, max_dd_max=args.max_dd_max, ntrades_min=args.ntrades_min)
        print(f"Wrote {out}: {rec}")

    if args.ab:
        df = run_ab(args.symbol, args.timeframe, args.years, cfg)
        out_csv = artifacts / "ab_results.csv"
        out_summary = artifacts / "ab_summary.txt"
        save_ab_results(df, out_csv, out_summary)
        print(f"Wrote {out_csv} and {out_summary}")


if __name__ == "__main__":
    main()
