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
from .exchange import Exchange, ExchangeError
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

    symbols = cfg.symbols_whitelist if int(getattr(cfg, "max_open_trades", 1)) > 1 else [cfg.symbol]
    logger.info(
        f"paper mode | symbols={symbols} timeframe={cfg.timeframe} iterations={max_iterations}"
    )

    # Track last signal timestamp per symbol to avoid duplicate entries on the same closed candle
    last_signal_ts: Dict[str, Optional[int]] = {s: None for s in symbols}

    def quote_from(symbol: str) -> str:
        return symbol.split("/")[-1] if "/" in symbol else "USDT"

    def per_pair_cap(symbol: str) -> float:
        # Try pair_caps map, fallback to max_notional_usdt_per_pair, then legacy per-trade cap
        if cfg.pair_caps and symbol in cfg.pair_caps:
            return float(cfg.pair_caps[symbol])
        if getattr(cfg, "max_notional_usdt_per_pair", None):
            return float(cfg.max_notional_usdt_per_pair)
        return float(cfg.max_notional_per_trade_usdt)

    def notional_open_for(symbol: str) -> float:
        if symbol not in broker.open_positions:
            return 0.0
        t = broker.open_positions[symbol]
        return float(t.entry_price) * float(t.qty)

    def correlation_guard(symbol_new: str, df_new: pd.DataFrame) -> bool:
        # Compute Pearson correlation between last N returns of symbol_new and each open symbol
        if not broker.open_positions:
            return True
        threshold = float(getattr(cfg, "correlation_threshold", 0.85))
        max_corr = int(getattr(cfg, "max_correlated_trades", 2))
        N = 100
        returns_new = df_new["close"].astype(float).pct_change().tail(N)
        correlated_count = 0
        for sym_open in list(broker.open_positions.keys()):
            if sym_open == symbol_new:
                continue
            try:
                candles = ex.fetch_ohlcv(sym_open, cfg.timeframe, limit=N + 5)
                df_o = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"]).sort_values("timestamp")
                returns_o = df_o["close"].astype(float).pct_change().tail(N)
                joined = pd.concat([returns_new.reset_index(drop=True), returns_o.reset_index(drop=True)], axis=1).dropna()
                if len(joined) < 10:
                    continue
                corr = joined.iloc[:, 0].corr(joined.iloc[:, 1])
                if pd.notna(corr) and corr > threshold:
                    correlated_count += 1
            except Exception:
                continue
        if correlated_count >= max_corr:
            logger.info(f"Skip {symbol_new}: correlation guard (count={correlated_count} >= {max_corr})")
            return False
        return True

    it = 0
    while it < max_iterations:
        it += 1
        for symbol in symbols:
            candles = ex.fetch_ohlcv(symbol, cfg.timeframe, limit=200)
            df = pd.DataFrame(
                candles, columns=["timestamp", "open", "high", "low", "close", "volume"]
            ).sort_values("timestamp")

            # Risk guard on realized PnL across all trades
            realized = [t.pnl for t in broker.trade_log if t.pnl is not None]
            if not max_daily_loss_guard(realized, float(env.BASE_EQUITY), float(env.MAX_DAILY_LOSS_PCT)):
                notifier.send("Max daily loss reached. Halting new entries.")
                break
            if kill_switch(realized, float(env.BASE_EQUITY), float(env.MAX_DAILY_LOSS_PCT)):
                logger.warning("Kill switch activated. Stopping loop.")
                break

            # Per-pair notional cap and global open trades cap
            if len(broker.open_positions) >= int(cfg.max_open_trades):
                continue
            if notional_open_for(symbol) >= per_pair_cap(symbol):
                continue

            sig = generate_signal(df[["open", "high", "low", "close", "volume"]], cfg)
            ref_ts = df.iloc[-2]["timestamp"]
            if sig != "buy" or last_signal_ts.get(symbol) == ref_ts:
                continue

            # Correlation guard
            if not correlation_guard(symbol, df):
                last_signal_ts[symbol] = ref_ts
                continue

            entry = float(df.iloc[-2]["close"])  # last closed
            stop = compute_stop(entry, atr=entry * 0.0 + 1.0, k=cfg.atr_k)  # placeholder ATR
            rr = float(cfg.risk_rr)
            tp = entry + (entry - stop) * rr
            try:
                qty = position_size(entry, stop, broker.equity, float(env.RISK_PER_TRADE_PCT), step=0.0)
            except Exception:
                qty = 0.0
            if qty > 0:
                t = broker.buy(symbol, entry, qty, stop, tp)
                last_signal_ts[symbol] = ref_ts
                msg = f"BUY {t.symbol} qty={t.qty} entry={t.entry_price} stop={t.stop_price} tp={t.take_profit}"
                logger.info(msg)
                notifier.send(msg)

        # Update stops/tps with the latest candle only for symbols we just processed
        # Using the last fetched df is fine for simplicity in this loop.
        # In a real loop, maintain per-symbol recent candles.
        broker.update_prices(df.tail(1))

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

    def per_pair_cap(symbol: str) -> float:
        if cfg.pair_caps and symbol in cfg.pair_caps:
            return float(cfg.pair_caps[symbol])
        if getattr(cfg, "max_notional_usdt_per_pair", None):
            return float(cfg.max_notional_usdt_per_pair)
        return float(cfg.max_notional_per_trade_usdt)

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

    def correlation_guard(symbol_new: str, df_new: pd.DataFrame) -> bool:
        threshold = float(getattr(cfg, "correlation_threshold", 0.85))
        max_corr = int(getattr(cfg, "max_correlated_trades", 2))
        N = 100
        returns_new = df_new["close"].astype(float).pct_change().tail(N)
        correlated_count = 0
        open_syms: Dict[str, bool] = {}
        # In live mode we don't track open positions here; rely on exchange/accounting integration later.
        # For now, we use last_signal_ts as a proxy to limit newly attempted entries across correlated pairs.
        for sym in cfg.symbols_whitelist:
            if sym == symbol_new:
                continue
            if last_signal_ts.get(sym) is None:
                continue
            try:
                candles = ex.fetch_ohlcv(sym, cfg.timeframe, limit=N + 5)
                df_o = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"]).sort_values("timestamp")
                returns_o = df_o["close"].astype(float).pct_change().tail(N)
                joined = pd.concat([returns_new.reset_index(drop=True), returns_o.reset_index(drop=True)], axis=1).dropna()
                if len(joined) < 10:
                    continue
                corr = joined.iloc[:, 0].corr(joined.iloc[:, 1])
                if pd.notna(corr) and corr > threshold:
                    correlated_count += 1
            except Exception:
                continue
        return correlated_count < max_corr

    it = 0
    while it < max_iterations:
        it += 1
        for symbol in cfg.symbols_whitelist:
            candles = ex.fetch_ohlcv(symbol, cfg.timeframe, limit=200)
            df = pd.DataFrame(
                candles, columns=["timestamp", "open", "high", "low", "close", "volume"]
            ).sort_values("timestamp")

            # Kill switch check
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

            # Notional cap per pair
            cap = per_pair_cap(symbol)
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
            notional = entry * qty
            if notional > cap:
                # resize to cap
                qty = cap / max(entry, 1e-12)

            # Correlation guard against recently signaled pairs
            if not correlation_guard(symbol, df):
                last_signal_ts[symbol] = ref_ts
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

    paper = bool(getattr(args, "paper", False))
    live = bool(getattr(args, "live", False))
    dry_run = bool(getattr(args, "dry_run", False))
    iters_arg = int(getattr(args, "iterations", 0) or 0)

    banner = (
        f"trade-bot starting | exchange={cfg.exchange} tf={cfg.timeframe} "
        f"paper={paper} live={live} dry_run={dry_run}"
    )
    logger.info(banner)
    notifier.send(banner)

    iters = iters_arg if iters_arg > 0 else 3
    if paper and not live:
        try:
            run_paper(cfg, env, max_iterations=iters, sleep_seconds=0)
        except ExchangeError as e:
            logger.warning(f"paper mode aborted due to exchange error: {e}")
    elif live:
        try:
            run_live(cfg, env, dry_run=dry_run, max_iterations=iters, sleep_seconds=0)
        except ExchangeError as e:
            logger.warning(f"live mode aborted due to exchange error: {e}")
    else:
        logger.info("No mode selected. Use --paper or --live.")


if __name__ == "__main__":
    main()
