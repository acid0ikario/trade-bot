You are acting as a senior trading infrastructure engineer. Extend the runner to support live trading with robust safety features.

Context

    Paper mode exists. Exchange wrapper enforces whitelist and notional caps.

Goals

    Live mode that uses real API keys, with dry-run capability and kill switch.

Tasks

    Runner changes (src/bot/runner.py):

        Add flags: --live, --dry-run.

        Live mode:
        • Load API keys from env.
        • Get free quote balance as equity.
        • Validate symbols_whitelist and max_notional_per_trade_usdt.

        On “buy”:
        • Compute qty via position_size.
        • Compute stop/TP (ATR or swing low; RR from config).
        • If NOT dry-run: create_market_buy then place_oco_takeprofit_stoploss.
        • Log order ids and send Telegram notification.

        Watcher/poller loop:
        • Track open orders and cancel the opposite leg when TP or SL fills.

        Kill switch:
        • If daily loss limit is breached (risk.kill_switch), stop sending new orders, log + notify.

    README updates (Go-Live Checklist):

        API keys: Spot-only, no withdrawals.

        Validate risk params in .env.

        Run paper for multiple days → dry-run → live.

        Monitor logs and Telegram alerts.

Acceptance criteria

    Live places real orders (when not dry-run) and logs everything.

    Dry-run prints intended actions without trading.

    Kill switch halts new orders on breach.

    Updated README with checklist.

––––––––––––––––––––––––––––––––––––