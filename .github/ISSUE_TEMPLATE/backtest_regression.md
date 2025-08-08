---
name: Backtest Regression
about: Regression detected in nightly backtest performance.
title: "Nightly backtest regression: {{ date }}"
labels: regression, backtest
assignees: ''
---
## Summary
A nightly backtest run detected potential performance regression.

- **Best Sharpe Ratio:** {{ best_sharpe }}
- **Worst Max Drawdown:** {{ worst_dd }}

See the attached artifacts for full details.

**Please investigate the parameter set(s) and recent code changes.**
