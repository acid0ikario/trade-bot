Extend runner to add `--live` mode:
- Fetch balance and compute size with live equity.
- Place market order and emulate OCO TP/SL via two GTC orders if needed, with asynchronous watcher that cancels the other when one fills.
- Safety: notional cap, daily loss guard reading closed PnL from recent trades.
- Dry-run flag that logs all would-be orders without sending.
Add README “Go-Live Checklist”.
Return changes.
