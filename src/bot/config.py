from __future__ import annotations
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os


class Fees(BaseModel):
    maker: float = 0.001
    taker: float = 0.001


class AppConfig(BaseModel):
    exchange: str = "binance"
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    slippage_bps: int = 5
    fees: Fees = Field(default_factory=Fees)

    risk_rr: float = 2.0
    atr_period: int = 14
    atr_k: float = 1.5
    ema_fast: int = 50
    ema_slow: int = 200
    rsi_period: int = 14
    rsi_buy_min: int = 45
    rsi_buy_max: int = 60

    max_notional_per_trade_usdt: float = 200
    max_open_trades: int = 1
    paper_trading: bool = True
    telegram_enabled: bool = False


class EnvVars(BaseModel):
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_API_SECRET: Optional[str] = None
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    BASE_EQUITY: float = 2000
    MAX_DAILY_LOSS_PCT: float = 0.03
    RISK_PER_TRADE_PCT: float = 0.01


def load_config(path: str | Path) -> tuple[AppConfig, EnvVars]:
    load_dotenv()
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    cfg = AppConfig(**raw)
    env_values = {k: os.getenv(k) for k in EnvVars.model_fields.keys()}
    env = EnvVars(**{k: v for k, v in env_values.items() if v is not None})
    return cfg, env
