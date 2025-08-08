"""Exchange adapter (stub). Real implementation comes in step 01."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from time import sleep
from typing import Any, Callable, Optional

import ccxt  # type: ignore
from loguru import logger

from .config import AppConfig, EnvVars


class ExchangeError(Exception):
    """Normalized exchange error for the app."""


RetryableCcxtErrors = (
    ccxt.NetworkError,
    ccxt.DDoSProtection,
    ccxt.RateLimitExceeded,
    ccxt.ExchangeNotAvailable,
    ccxt.RequestTimeout,
)


@dataclass
class _RetryPolicy:
    tries: int = 3
    base_delay: float = 0.1  # seconds
    max_delay: float = 1.0


class Exchange:
    """Binance Spot exchange wrapper with safety guardrails."""

    def __init__(
        self,
        cfg: AppConfig,
        env: Optional[EnvVars] = None,
        *,
        max_retries: int = 3,
        backoff_base_delay: float = 0.05,
        timeout_ms: int = 15000,
    ) -> None:
        self.cfg = cfg
        self.env = env or EnvVars()
        self.symbols_whitelist = set(cfg.symbols_whitelist)
        self.max_notional_usdt = float(cfg.max_notional_per_trade_usdt)
        self._retry = _RetryPolicy(tries=max_retries, base_delay=backoff_base_delay)

        creds = {
            "apiKey": self.env.BINANCE_API_KEY,
            "secret": self.env.BINANCE_API_SECRET,
        }
        # Remove None values to avoid ccxt warnings
        creds = {k: v for k, v in creds.items() if v}

        self.client = ccxt.binance(
            {
                **creds,
                "enableRateLimit": True,
                "timeout": timeout_ms,
                "options": {
                    "defaultType": "spot",
                },
            }
        )

        # Load markets (metadata contains filters)
        try:
            self.markets = self.client.load_markets()
        except RetryableCcxtErrors as e:  # type: ignore[misc]
            # try once more quickly to populate metadata, otherwise proceed lazily
            logger.warning(f"load_markets failed transiently: {e}. Will retry lazily later.")
            self.markets = {}
        except ccxt.BaseError as e:
            logger.warning(f"load_markets failed: {e}. Will retry lazily when needed.")
            self.markets = {}

    # ---------- helpers ----------
    def _with_retries(self, func: Callable[[], Any]) -> Any:
        delay = self._retry.base_delay
        last_err: Optional[Exception] = None
        for attempt in range(1, self._retry.tries + 1):
            try:
                return func()
            except RetryableCcxtErrors as e:  # type: ignore[misc]
                last_err = e
                if attempt == self._retry.tries:
                    break
                logger.warning(
                    f"Transient exchange error (attempt {attempt}/{self._retry.tries}): {e}. Retrying in {delay:.2f}s"
                )
                sleep(min(delay, self._retry.max_delay))
                delay = min(delay * 2, self._retry.max_delay)
            except ccxt.BaseError as e:  # non-retryable ccxt error
                raise ExchangeError(str(e)) from e
            except Exception as e:  # any other error
                raise ExchangeError(str(e)) from e
        assert last_err is not None
        raise ExchangeError(str(last_err)) from last_err

    @staticmethod
    def _floor_to_step(value: float, step: float) -> float:
        if step <= 0:
            return value
        # Use Decimal to avoid FP drift
        d = Decimal(str(value))
        s = Decimal(str(step))
        return float((d // s) * s)

    @staticmethod
    def _round_to_tick(value: float, tick_size: float) -> float:
        if tick_size <= 0:
            return value
        d = Decimal(str(value))
        t = Decimal(str(tick_size))
        return float((d / t).quantize(Decimal("1"), rounding=ROUND_FLOOR) * t)

    @staticmethod
    def _clip_notional(symbol: str, qty: float, price: float, max_notional: float) -> float:
        if max_notional <= 0:
            return qty
        notional = qty * price
        if notional <= max_notional:
            return qty
        new_qty = max_notional / price
        return max(new_qty, 0.0)

    def _ensure_markets(self) -> None:
        if not self.markets:
            self.markets = self.client.load_markets()

    def _check_symbol_allowed(self, symbol: str) -> None:
        if symbol not in self.symbols_whitelist:
            raise ExchangeError(f"Symbol {symbol} not in whitelist")

    def _filters(self, symbol: str) -> dict[str, Any]:
        self._ensure_markets()
        m = self.client.market(symbol)
        info = m.get("info", {})
        filters = info.get("filters", []) or []
        by_type = {f.get("filterType"): f for f in filters if isinstance(f, dict)}
        step_size = float(by_type.get("LOT_SIZE", {}).get("stepSize") or 0) or float(
            m.get("precision", {}).get("amount", 0)
        )
        min_qty = float(by_type.get("LOT_SIZE", {}).get("minQty") or 0) or float(
            ((m.get("limits", {}) or {}).get("amount", {}) or {}).get("min", 0)
        )
        # MIN_NOTIONAL renamed to NOTIONAL in newer API
        min_notional = float(
            (by_type.get("MIN_NOTIONAL", {}) or {}).get("minNotional")
            or (by_type.get("NOTIONAL", {}) or {}).get("minNotional")
            or ((m.get("limits", {}) or {}).get("cost", {}) or {}).get("min", 0)
            or 0
        )
        # price tick
        tick_size = float(by_type.get("PRICE_FILTER", {}).get("tickSize") or 0) or float(
            m.get("precision", {}).get("price", 0)
        )
        return {
            "step_size": float(step_size) if step_size else 0.0,
            "min_qty": float(min_qty) if min_qty else 0.0,
            "min_notional": float(min_notional) if min_notional else 0.0,
            "tick_size": float(tick_size) if tick_size else 0.0,
        }

    # ---------- public API ----------
    def get_price(self, symbol: str) -> float:
        self._check_symbol_allowed(symbol)

        def _op():
            t = self.client.fetch_ticker(symbol)
            price = t.get("last") or t.get("close") or t.get("info", {}).get("lastPrice")
            if price is None:
                raise ExchangeError("No price in ticker response")
            return float(price)

        return float(self._with_retries(_op))

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> list[list[Any]]:
        self._check_symbol_allowed(symbol)

        def _op():
            candles = self.client.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            if not isinstance(candles, list):
                raise ExchangeError("OHLCV response malformed")
            return candles

        return self._with_retries(_op)

    def get_balance(self, quote: str) -> float:
        def _op():
            bal = self.client.fetch_balance()
            free = bal.get("free", {}).get(quote)
            if free is None:
                free = (bal.get(quote, {}) or {}).get("free")
            if free is None:
                raise ExchangeError(f"Balance for {quote} not found")
            return float(free)

        return float(self._with_retries(_op))

    def _prepare_order_qty(self, symbol: str, qty: float, price: Optional[float] = None) -> float:
        if qty <= 0:
            raise ExchangeError("Quantity must be positive")
        self._check_symbol_allowed(symbol)
        filters = self._filters(symbol)
        if price is None:
            price = self.get_price(symbol)
        # enforce notional cap: raise if exceeded
        if qty * price > self.max_notional_usdt:
            raise ExchangeError(
                f"Notional {qty * price:.8f} exceeds max_notional_per_trade_usdt {self.max_notional_usdt}"
            )
        # apply lot size floor
        step = float(filters["step_size"]) or 0.0
        adj_qty = self._floor_to_step(qty, step) if step > 0 else qty
        # ensure meets min qty and min notional
        if filters["min_qty"] and adj_qty < float(filters["min_qty"]):
            raise ExchangeError(
                f"Quantity {adj_qty} below minQty {filters['min_qty']} for {symbol}"
            )
        if filters["min_notional"] and adj_qty * price < float(filters["min_notional"]):
            raise ExchangeError(
                f"Notional {adj_qty * price:.8f} below minNotional {filters['min_notional']} for {symbol}"
            )
        if adj_qty <= 0:
            raise ExchangeError("Quantity becomes zero after adjustments")
        return adj_qty

    def create_market_buy(self, symbol: str, qty: float) -> dict:
        price = self.get_price(symbol)
        adj_qty = self._prepare_order_qty(symbol, qty, price)
        logger.info(f"Create MARKET BUY {symbol} qty={adj_qty}")

        def _op():
            return self.client.create_order(symbol, "market", "buy", adj_qty)

        return self._with_retries(_op)

    def create_market_sell(self, symbol: str, qty: float) -> dict:
        price = self.get_price(symbol)
        adj_qty = self._prepare_order_qty(symbol, qty, price)
        logger.info(f"Create MARKET SELL {symbol} qty={adj_qty}")

        def _op():
            return self.client.create_order(symbol, "market", "sell", adj_qty)

        return self._with_retries(_op)

    def place_oco_takeprofit_stoploss(
        self, symbol: str, qty: float, tp_price: float, sl_price: float
    ) -> dict:
        self._check_symbol_allowed(symbol)
        filters = self._filters(symbol)
        # Adjust prices to ticks
        tp_price_adj = self._round_to_tick(tp_price, float(filters["tick_size"]) or 0.0)
        sl_price_adj = self._round_to_tick(sl_price, float(filters["tick_size"]) or 0.0)
        last_price = self.get_price(symbol)
        adj_qty = self._prepare_order_qty(symbol, qty, last_price)

        logger.info(
            f"Place OCO-emulated orders {symbol} qty={adj_qty} TP={tp_price_adj} SL={sl_price_adj}"
        )

        def _op():
            # Take-profit limit sell
            tp = self.client.create_order(symbol, "limit", "sell", adj_qty, tp_price_adj)
            # Stop-loss: stop-limit with stopPrice and price
            sl_params = {"stopPrice": sl_price_adj}
            sl = self.client.create_order(
                symbol, "stop_loss_limit", "sell", adj_qty, sl_price_adj, params=sl_params
            )
            return {
                "tp_order_id": tp.get("id"),
                "sl_order_id": sl.get("id"),
                "tp": tp,
                "sl": sl,
            }

        return self._with_retries(_op)

    # NEVER implement any withdrawal functions in this class.
