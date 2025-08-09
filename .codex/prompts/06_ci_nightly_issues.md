You are acting as a DevOps engineer. Enhance the nightly CI workflow to detect performance regressions automatically and open actionable issues.

Context

- Project: trade-bot (Python 3.11, Poetry, pytest, ruff).
- Nightly workflow runs a backtest and uploads artifacts.
- Artifacts include a CSV with metrics per run/parameter set.

Goals

- Parse nightly backtest results, compare against thresholds, and open a GitHub Issue when a regression is detected.
- Always upload artifacts and a machine-readable summary.

Tasks

1) Workflow updates: `.github/workflows/nightly.yml`
- Ensure the workflow uses Python 3.11 and Poetry cache.
- After the backtest step writes `data/artifacts/backtest_results.csv`, run a Python script to evaluate metrics and export a decision.
- Provide defaults via env with override capability:
  - `SHARPE_THRESHOLD` default: `1.0` (minimum acceptable best Sharpe)
  - `MAX_DD_THRESHOLD` default: `-0.20` (minimum acceptable worst Max Drawdown; more negative is worse)
- The script must:
  - Read `data/artifacts/backtest_results.csv` (required columns: `Sharpe`, `MaxDD`).
  - Compute: `best_sharpe = max(Sharpe)`, `worst_dd = min(MaxDD)`.
  - Produce `data/artifacts/summary.json` with: `{ "best_sharpe": float, "worst_dd": float, "thresholds": { ... }, "timestamp": ISO8601 }`.
  - Decide `regression = (best_sharpe < SHARPE_THRESHOLD) or (worst_dd < MAX_DD_THRESHOLD)`.
  - Emit a job output named `regression_detected` (`true|false`) via `$GITHUB_OUTPUT` and also write an environment variable `REGRESSION_DETECTED` for downstream steps.
- Always upload `data/artifacts/` as an artifact named `nightly-artifacts`.

2) Add evaluator script: `src/bot/ci_regression.py`
- CLI usage: `python -m bot.ci_regression --csv data/artifacts/backtest_results.csv --out data/artifacts/summary.json` and respects optional env thresholds.
- Validate CSV presence and columns; exit non-zero on parse error to fail the job early.
- Print a concise summary to STDOUT.

3) Create issue on regression
- Add a conditional workflow step that runs when `regression_detected == 'true'`.
- Use `actions/github-script` (preferred) or REST API to open an issue:
  - Title: `Nightly backtest regression detected`
  - Labels: `regression`, `backtest`
  - Body: Rendered from a new issue template with placeholders replaced using values from `summary.json`.
- Upload or link the `nightly-artifacts` artifact in the issue body.

4) Issue template: `.github/ISSUE_TEMPLATE/backtest_regression.md`
- Front matter:
  ```yaml
  name: Backtest Regression
  about: Regression detected in nightly backtest performance
  title: "Nightly backtest regression: {{ date }}"
  labels: [regression, backtest]
  assignees: []
  ```
- Body:
  - Summary paragraph.
  - Metrics:
    - Best Sharpe: `{{ best_sharpe }}`
    - Worst Max Drawdown: `{{ worst_dd }}`
  - Thresholds:
    - SHARPE_THRESHOLD: `{{ sharpe_threshold }}`
    - MAX_DD_THRESHOLD: `{{ max_dd_threshold }}`
  - Links to the uploaded artifact(s) and any relevant run URLs.
  - Action item checklist to investigate parameter changes and recent commits.

5) Documentation
- Update `README.md` CI section with a short description of nightly regression checks and how to adjust thresholds via repository secrets/variables.

Acceptance criteria

- The nightly job uploads `nightly-artifacts` containing `backtest_results.csv` and `summary.json` on every run.
- When thresholds are breached, a GitHub issue is created with the metrics and links to artifacts; no issue is created when within limits.
- The evaluator script exits cleanly, sets the job output, and writes `summary.json` in a stable schema.
- Workflow remains green if the CSV exists and parsing succeeds, and fails early on malformed/missing artifacts.
- No external network calls beyond GitHub Actions’ own APIs.

Implementation hints

- Use `python - <<'PY'
  ...
  PY` for an inline script or add a dedicated module `bot/ci_regression.py` and call it.
- Use `echo "regression_detected=$VALUE" >> "$GITHUB_OUTPUT"` to set the output.
- CSV column names should match backtester outputs; if needed, add a mapping or assert present columns.