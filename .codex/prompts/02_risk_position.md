Create src/bot/risk.py and src/bot/position.py:
- risk.py: compute stop loss using recent swing low/high or ATR*k (k from config), max_daily_loss_guard(state), and kill_switch(state).
- position.py: position_size(entry, stop, equity, risk_pct) with flooring to exchange lot size.
- tests for both modules; include edge cases (tiny ATR, tight stop).
Return changed files.
