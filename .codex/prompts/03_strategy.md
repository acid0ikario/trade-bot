Implement src/bot/strategy.py:
- Indicators: EMA(fast=50), EMA(slow=200), RSI(14).
- Long entry: EMAfast > EMAslow, RSI within [rsi_buy_min, rsi_buy_max], candle closes above EMAfast, pullback confirmation (previous close > current close).
- Exit: TP at R:R >= config.risk_rr; SL at stop derived from risk module.
- No shorts initially.
- All logic must operate on candle-close signals (no intrabar lookahead).
- Add tests verifying signals on synthetic data.
Return changes.
