Implement src/bot/backtest.py and src/bot/metrics.py:
- Backtesting wrapper to run parameter grid (ema_fast, ema_slow, rsi window/bounds, atr k, rr).
- Metrics: CAGR, Sharpe (simple), Max Drawdown, Winrate, Profit Factor, Expectancy, Avg Trade.
- Output: CSV summary + per-run equity curve PNG/HTML (plotly ok).
- Add CLI: `python -m bot.backtest --symbol BTC/USDT --timeframe 1h --years 2 --grid default`.
- Tests for metrics correctness on synthetic series.
Return changes.
