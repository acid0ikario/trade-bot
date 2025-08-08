Enhance .github/workflows/nightly.yml to:
- Run backtests on a small grid.
- Upload artifacts (CSV + plots).
- If best Sharpe < threshold or MaxDD > threshold, create a GitHub Issue summarizing stats and pointing to artifacts.
Implement .github/ISSUE_TEMPLATE/backtest_regression.md.
Return changes.
