from typing import Optional, List, Dict

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

    # Legacy per-trade cap (kept for backward compatibility)
    max_notional_per_trade_usdt: float = 200

    # New: multi-pair & correlation-aware limits
    max_notional_usdt_per_pair: float = 200
    max_correlated_trades: int = 2
    correlation_threshold: float = 0.85

    max_open_trades: int = 1
    paper_trading: bool = True
    telegram_enabled: bool = False

    # Whitelist of tradable symbols
    symbols_whitelist: List[str] = Field(default_factory=lambda: ["BTC/USDT", "ETH/USDT", "BNB/USDT"])

    # Optional per-pair caps mapping (symbol -> usdt cap). Falls back to max_notional_usdt_per_pair when missing
    pair_caps: Dict[str, float] = Field(default_factory=dict)


class EnvVars(BaseModel):
    BINANCE_API_KEY: Optional[str] = None
    BINANCE_API_SECRET: Optional[str] = None
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    BASE_EQUITY: float = 2000
    MAX_DAILY_LOSS_PCT: float = 0.03
    RISK_PER_TRADE_PCT: float = 0.01


def _load_pair_caps(pairs_path: str) -> Dict[str, float]:
    if not os.path.exists(pairs_path):
        return {}
    with open(pairs_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    caps: Dict[str, float] = {}
    for k, v in raw.items():
        sym = k if "/" in k else f"{k}/USDT"
        try:
            caps[sym] = float(v)
        except Exception:
            continue
    return caps


def load_config(path):
    # type: (str) -> tuple[AppConfig, EnvVars]
    load_dotenv()
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # Optionally load per-pair caps from sibling pairs.yaml
    cfg_dir = os.path.dirname(os.path.abspath(path))
    pairs_path = os.path.join(cfg_dir, "pairs.yaml")
    pair_caps = _load_pair_caps(pairs_path)
    if pair_caps:
        raw["pair_caps"] = pair_caps

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
