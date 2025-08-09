from typing import Optional, List

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

    # New: whitelist of tradable symbols
    symbols_whitelist: List[str] = Field(default_factory=lambda: ["BTC/USDT"])


class EnvVars(BaseModel):
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_API_SECRET: Optional[str] = None
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    BASE_EQUITY: float = 2000
    MAX_DAILY_LOSS_PCT: float = 0.03
    RISK_PER_TRADE_PCT: float = 0.01


def load_config(path):
    # type: (str) -> tuple[AppConfig, EnvVars]
    load_dotenv()
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    cfg = AppConfig(**raw)
    # Pydantic v2 uses model_fields, v1 uses __fields__; support both
    field_names = []  # type: List[str]
    if hasattr(EnvVars, "model_fields"):
        field_names = list(getattr(EnvVars, "model_fields").keys())
    elif hasattr(EnvVars, "__fields__"):
        field_names = list(getattr(EnvVars, "__fields__").keys())
    env_values = {k: os.getenv(k) for k in field_names}
    env = EnvVars(**{k: v for k, v in env_values.items() if v is not None})
    return cfg, env
