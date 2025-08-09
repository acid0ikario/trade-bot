---
name: Backtest Regression
about: Regression detected in nightly backtest performance
title: "Nightly backtest regression: {{ date }}"
labels: [regression, backtest]
assignees: []
---

## Summary

A performance regression was detected in the nightly backtest run.

- Best Sharpe: `{{ best_sharpe }}`
- Worst Max Drawdown: `{{ worst_dd }}`

### Thresholds
- SHARPE_THRESHOLD: `{{ sharpe_threshold }}`
- MAX_DD_THRESHOLD: `{{ max_dd_threshold }}`

### Artifacts
See the uploaded `nightly-artifacts` for CSV and summary JSON.

### Action items
- [ ] Investigate parameter grid changes
- [ ] Review recent commits affecting strategy or risk
- [ ] Re-run locally to reproduce
