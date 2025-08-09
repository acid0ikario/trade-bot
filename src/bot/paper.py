"""Paper trading engine implementation."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

import pandas as pd

from .config import AppConfig


@dataclass
class Trade:
    symbol: str
    side: str  # "buy" or "sell"
    entry_price: float
    stop_price: float
    take_profit: float
    qty: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: Optional[float] = None


class PaperBroker:
    def __init__(self, cfg: AppConfig, equity: float) -> None:
        self.cfg = cfg
        self.equity = float(equity)
        self.open_positions: Dict[str, Trade] = {}
        self.trade_log: List[Trade] = []

    def _apply_slippage(self, price: float, side: str) -> float:
        bps = float(getattr(self.cfg, "slippage_bps", 0) or 0)
        factor = 1.0 + (bps / 10000.0)
        if side == "buy":
            return price * factor
        return price / factor  # favorable for sell if factor>1

    def _taker_fee(self, notional: float) -> float:
        fee_rate = float(self.cfg.fees.taker if self.cfg and self.cfg.fees else 0.0)
        return abs(notional) * fee_rate

    def buy(self, symbol: str, price: float, qty: float, stop: float, tp: float) -> Trade:
        fill_price = self._apply_slippage(float(price), "buy")
        notional = fill_price * float(qty)
        fee = self._taker_fee(notional)
        # Cash outflow
        self.equity -= notional + fee
        trade = Trade(
            symbol=symbol,
            side="buy",
            entry_price=float(fill_price),
            stop_price=float(stop),
            take_profit=float(tp),
            qty=float(qty),
            entry_time=datetime.utcnow(),
        )
        self.open_positions[symbol] = trade
        return trade

    def sell(self, symbol: str, price: float, qty: float) -> Optional[Trade]:
        if symbol not in self.open_positions:
            return None
        trade = self.open_positions.pop(symbol)
        fill_price = self._apply_slippage(float(price), "sell")
        proceeds = float(qty) * fill_price
        fee = self._taker_fee(proceeds)
        # Cash inflow
        self.equity += proceeds - fee
        pnl = (fill_price - trade.entry_price) * float(qty) - self._taker_fee(trade.entry_price * float(qty)) - fee
        trade.exit_price = float(fill_price)
        trade.exit_time = datetime.utcnow()
        trade.pnl = float(pnl)
        self.trade_log.append(trade)
        return trade

    def update_prices(self, candles_df: pd.DataFrame) -> None:
        if not self.open_positions:
            return
        # Consider last candle only by default
        df = candles_df.tail(1)
        row = df.iloc[-1]
        high = float(row["high"]) if "high" in df.columns else float(row[2])
        low = float(row["low"]) if "low" in df.columns else float(row[3])
        for symbol, trade in list(self.open_positions.items()):
            # Stop first, then TP for conservative handling
            if low <= trade.stop_price <= high:
                self.sell(symbol, trade.stop_price, trade.qty)
            elif low <= trade.take_profit <= high:
                self.sell(symbol, trade.take_profit, trade.qty)
