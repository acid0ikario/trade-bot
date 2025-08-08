Implement src/bot/paper.py and src/bot/runner.py:
- paper.py: simulate orders, PnL, fees (maker/taker from config), slippage (bps).
- runner.py: main loop, loads config + .env; 
  1) fetch last N candles; 
  2) generate signal using strategy; 
  3) check guards (max daily loss, kill switch); 
  4) compute size; 
  5) simulate/execute order (paper first).
- Add CLI: `python -m bot.runner --paper --config config/config.yaml`.
- Add logging with loguru; Telegram notifier on entries/exits and when guards trigger.
- Tests: deterministic paper fills and guard triggers.
Return changes.
