from __future__ import annotations
import argparse
from pathlib import Path
from time import sleep
from datetime import datetime

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", action="store_true", help="Run in paper mode")
    parser.add_argument("--live", action="store_true", help="Run in live mode")
    parser.add_argument("--config", type=str, default="config/config.yaml")
    parser.add_argument("--iterations", type=int, default=0, help="Max iterations for paper mode")
    args = parser.parse_args()

    logger = setup_logger()
    cfg, env = load_config(Path(args.config))

    notifier = Notifier(
        enabled=cfg.telegram_enabled,
        token=env.TELEGRAM_BOT_TOKEN,
        chat_id=env.TELEGRAM_CHAT_ID,
    )

    banner = (
        f"trade-bot starting | exchange={cfg.exchange} symbol={cfg.symbol} tf={cfg.timeframe} "
        f"paper={args.paper} live={args.live}"
    )
    logger.info(banner)
    notifier.send(banner)

    if args.paper and not args.live:
        max_iters = args.iterations if args.iterations > 0 else 3
        run_paper(cfg, env, max_iterations=max_iters, sleep_seconds=0)
    else:
        logger.info("Live mode not implemented yet.")


if __name__ == "__main__":
    main()
