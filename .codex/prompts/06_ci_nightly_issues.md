You are acting as a DevOps engineer. Enhance the nightly CI workflow and add automated regression issues.

Context

    The GitHub Actions nightly.yml runs a daily backtest and uploads artifacts.

    We want to detect performance degradation and automatically file an issue.

Goals

    Parse backtest results, compare to thresholds, and open a GitHub Issue when necessary.

Tasks

    Nightly workflow changes (.github/workflows/nightly.yml):

        After the backtest step, run a Python snippet that parses data/artifacts/backtest_results.csv.

        Compute:
        • best Sharpe ratio (max)
        • worst max drawdown (min, negative numbers are worse)

        Thresholds via env:
        • SHARPE_THRESHOLD default 1.0
        • MAX_DD_THRESHOLD default -0.20

        If best_sharpe < SHARPE_THRESHOLD OR worst_dd < MAX_DD_THRESHOLD:
        • write summary.json with metrics
        • set an output or env flag to signal regression (e.g., REGRESSION_DETECTED=true)

    Create issue when regression is detected:

        Conditional step uses actions/github-script (or REST API) to open issue:
        • Title: “Nightly backtest regression detected”
        • Body from .github/ISSUE_TEMPLATE/backtest_regression.md
        • Include metrics from summary.json and link/upload artifacts.
    Issue template (.github/ISSUE_TEMPLATE/backtest_regression.md):
    name: Backtest Regression
    about: Regression detected in nightly backtest performance.
    title: "Nightly backtest regression: {{ date }}"
    labels: regression, backtest
    assignees: ''
    Summary

    Nightly backtest indicates potential performance regression.

        Best Sharpe: {{ best_sharpe }}

        Worst Max Drawdown: {{ worst_dd }}
        See attached artifacts for details.
        Action: Investigate parameter sets and recent changes.

Acceptance criteria

    Nightly job always uploads artifacts and summary.

    On threshold breach, an issue is created with metrics and artifact references.

    No issue if metrics are within limits.

––––––––––––––––––––––––––––––––––––