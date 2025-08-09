import argparse
import csv
import json
import os
from datetime import datetime, timezone


def evaluate(csv_path: str, out_path: str) -> bool:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    sharpe_threshold = float(os.getenv("SHARPE_THRESHOLD", "1.0"))
    max_dd_threshold = float(os.getenv("MAX_DD_THRESHOLD", "-0.20"))

    best_sharpe = float("-inf")
    worst_dd = float("inf")

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = [c.lower() for c in reader.fieldnames or []]
        # Accept typical variations
        def get(row, *names):
            for n in names:
                if n in row:
                    return row[n]
                # try case-insensitive
                for k, v in row.items():
                    if k.lower() == n.lower():
                        return v
            return None

        if not cols:
            raise ValueError("Empty CSV or no header")

        # Try to find expected columns
        sharpe_cols = ["sharpe"]
        dd_cols = ["max_dd", "maxdd", "max_drawdown"]

        for row in reader:
            s = get(row, *sharpe_cols)
            d = get(row, *dd_cols)
            if s is None or d is None:
                raise ValueError("Missing required columns Sharpe/MaxDD in CSV")
            try:
                s = float(s)
                d = float(d)
            except Exception:
                continue
            if s > best_sharpe:
                best_sharpe = s
            if d < worst_dd:
                worst_dd = d

    if best_sharpe == float("-inf") or worst_dd == float("inf"):
        raise ValueError("Could not parse metrics from CSV")

    summary = {
        "best_sharpe": best_sharpe,
        "worst_dd": worst_dd,
        "thresholds": {
            "SHARPE_THRESHOLD": sharpe_threshold,
            "MAX_DD_THRESHOLD": max_dd_threshold,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    regression = (best_sharpe < sharpe_threshold) or (worst_dd < max_dd_threshold)
    print(
        f"Summary: best_sharpe={best_sharpe:.3f}, worst_dd={worst_dd:.3f}, "
        f"thresholds(sharpe={sharpe_threshold}, max_dd={max_dd_threshold}), regression={regression}"
    )
    return regression


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    reg = evaluate(args.csv, args.out)

    # Emit job output and env
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as f:
            f.write(f"regression_detected={'true' if reg else 'false'}\n")
    print(f"REGRESSION_DETECTED={'true' if reg else 'false'}")

    # Also write an env file if provided
    gh_env = os.environ.get("GITHUB_ENV")
    if gh_env:
        with open(gh_env, "a", encoding="utf-8") as f:
            f.write(f"REGRESSION_DETECTED={'true' if reg else 'false'}\n")

    # Non-zero exit on parse error only; not on regression
    # This keeps the workflow green while still opening issues.


if __name__ == "__main__":
    main()
