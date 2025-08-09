from __future__ import annotations
import argparse
from pathlib import Path
from time import sleep
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from .logger import setup_logger
from .config import load_config, AppConfig, EnvVars
from .notifier import Notifier
from .exchange import Exchange
from .strategy import generate_signal
from .position import position_size
from .risk import compute_stop, max_daily_loss_guard, kill_switch
from .paper import PaperBroker


def run_paper(cfg: AppConfig, env: EnvVars, *, max_iterations: int = 3, sleep_seconds: int = 0):
    logger = setup_logger()
    notifier = Notifier(
        enabled=cfg.telegram_enabled,
        token=env.TELEGRAM_BOT_TOKEN,
        chat_id=env.TELEGRAM_CHAT_ID,
    )
    ex = Exchange(cfg, env)
    broker = PaperBroker(cfg, equity=float(env.BASE_EQUITY))

    logger.info(
        f"paper mode | symbol={cfg.symbol} timeframe={cfg.timeframe} iterations={max_iterations}"
    )

    last_signal_ts = None  # avoid duplicate entries on the same closed candle
    it = 0
    while it < max_iterations:
        it += 1
        candles = ex.fetch_ohlcv(cfg.symbol, cfg.timeframe, limit=200)
        # ccxt OHLCV: [timestamp, open, high, low, close, volume]
        df = pd.DataFrame(
            candles, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df = df.sort_values("timestamp")

        sig = generate_signal(df[["open", "high", "low", "close", "volume"]], cfg)
        ref_ts = df.iloc[-2]["timestamp"]
        if sig == "buy" and cfg.symbol not in broker.open_positions and last_signal_ts != ref_ts:
            entry = float(df.iloc[-2]["close"])  # last closed
            stop = compute_stop(entry, atr=entry * 0.0 + 1.0, k=cfg.atr_k)  # placeholder ATR
            rr = float(cfg.risk_rr)
            tp = entry + (entry - stop) * rr
            try:
                qty = position_size(entry, stop, broker.equity, float(env.RISK_PER_TRADE_PCT), step=0.0)
            except Exception:
                qty = 0.0
            if qty > 0:
                t = broker.buy(cfg.symbol, entry, qty, stop, tp)
                last_signal_ts = ref_ts
                msg = f"BUY {t.symbol} qty={t.qty} entry={t.entry_price} stop={t.stop_price} tp={t.take_profit}"
                logger.info(msg)
                notifier.send(msg)

        # Update stops/tps with the latest candle only
        broker.update_prices(df.tail(1))

        # Risk guards on realized PnL
        realized = [t.pnl for t in broker.trade_log if t.pnl is not None]
        if not max_daily_loss_guard(realized, float(env.BASE_EQUITY), float(env.MAX_DAILY_LOSS_PCT)):
            notifier.send("Max daily loss reached. Halting new entries.")
            break
        if kill_switch(realized, float(env.BASE_EQUITY), float(env.MAX_DAILY_LOSS_PCT)):
            logger.warning("Kill switch activated. Stopping loop.")
            break

        if sleep_seconds:
            sleep(sleep_seconds)

    return broker


def run_live(cfg: AppConfig, env: EnvVars, *, dry_run: bool = False, max_iterations: int = 1, sleep_seconds: int = 0):
    logger = setup_logger()
    notifier = Notifier(
        enabled=cfg.telegram_enabled,
        token=env.TELEGRAM_BOT_TOKEN,
        chat_id=env.TELEGRAM_CHAT_ID,
    )

    # Validate config
    if not cfg.symbols_whitelist or float(cfg.max_notional_per_trade_usdt) <= 0:
        raise ValueError("symbols_whitelist and max_notional_per_trade_usdt must be set for live mode")

    ex = Exchange(cfg, env)

    # Determine base equity from quote balance or fallback
    def quote_from(symbol: str) -> str:
        return symbol.split("/")[-1] if "/" in symbol else "USDT"

    quote = quote_from(cfg.symbols_whitelist[0])
    try:
        base_equity = float(ex.get_balance(quote))
    except Exception:
        base_equity = float(env.BASE_EQUITY)

    logger.info(
        f"live mode | dry_run={dry_run} timeframe={cfg.timeframe} symbols={cfg.symbols_whitelist} equity={base_equity}"
    )

    last_signal_ts: Dict[str, Optional[int]] = {s: None for s in cfg.symbols_whitelist}

    it = 0
    while it < max_iterations:
        it += 1
        for symbol in cfg.symbols_whitelist:
            candles = ex.fetch_ohlcv(symbol, cfg.timeframe, limit=200)
            df = pd.DataFrame(
                candles, columns=["timestamp", "open", "high", "low", "close", "volume"]
            ).sort_values("timestamp")

            # Kill switch check (use realized PnL list if available; here we track none -> rely on base equity)
            if kill_switch([], base_equity, float(env.MAX_DAILY_LOSS_PCT)):
                logger.warning("Kill switch engaged; skipping new entries.")
                notifier.send("Kill switch engaged; skipping new entries.")
                continue

            sig = generate_signal(df[["open", "high", "low", "close", "volume"]], cfg)
            ref_ts = df.iloc[-2]["timestamp"]
            if sig != "buy" or last_signal_ts.get(symbol) == ref_ts:
                continue

            entry = float(df.iloc[-2]["close"])  # last closed candle
            stop = compute_stop(entry, atr=1.0, k=cfg.atr_k)
            tp = entry + (entry - stop) * float(cfg.risk_rr)

            # Equity for sizing: refresh quote each loop, fallback to base_equity
            try:
                equity_now = float(ex.get_balance(quote))
            except Exception:
                equity_now = base_equity

            try:
                qty = position_size(entry, stop, equity_now, float(env.RISK_PER_TRADE_PCT), step=0.0)
            except Exception:
                qty = 0.0
            if qty <= 0:
                continue

            if dry_run:
                msg = f"DRY-RUN would BUY {symbol} qty={qty:.8f} entry={entry} stop={stop} tp={tp}"
                logger.info(msg)
                notifier.send(msg)
                last_signal_ts[symbol] = ref_ts
                continue

            # Place real orders
            buy_res = ex.create_market_buy(symbol, qty)
            oco_res = ex.place_oco_takeprofit_stoploss(symbol, qty, tp, stop)
            last_signal_ts[symbol] = ref_ts
            msg = (
                f"LIVE BUY {symbol} qty={qty:.8f} entry={entry} -> order={buy_res.get('id')} "
                f"oco(tp={oco_res.get('tp_order_id')}, sl={oco_res.get('sl_order_id')})"
            )
            logger.info(msg)
            notifier.send(msg)

        if sleep_seconds:
            sleep(sleep_seconds)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", action="store_true", help="Run in paper mode")
    parser.add_argument("--live", action="store_true", help="Run in live mode")
    parser.add_argument("--dry-run", action="store_true", help="Do not place orders; log intents only")
    parser.add_argument("--config", type=str, default="config/config.yaml")
    parser.add_argument("--iterations", type=int, default=0, help="Max iterations for loops")
    args = parser.parse_args()

    logger = setup_logger()
    cfg, env = load_config(Path(args.config))

    notifier = Notifier(
        enabled=cfg.telegram_enabled,
        token=env.TELEGRAM_BOT_TOKEN,
        chat_id=env.TELEGRAM_CHAT_ID,
    )

    banner = (
        f"trade-bot starting | exchange={cfg.exchange} tf={cfg.timeframe} "
        f"paper={args.paper} live={args.live} dry_run={args.dry_run}"
    )
    logger.info(banner)
    notifier.send(banner)

    iters = args.iterations if args.iterations > 0 else 3
    if args.paper and not args.live:
        run_paper(cfg, env, max_iterations=iters, sleep_seconds=0)
    elif args.live:
        run_live(cfg, env, dry_run=args.dry_run, max_iterations=iters, sleep_seconds=0)
    else:
        logger.info("No mode selected. Use --paper or --live.")


if __name__ == "__main__":
    main()
