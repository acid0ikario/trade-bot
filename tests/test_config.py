from bot.config import load_config
from pathlib import Path

def test_load_example_config():
    cfg, env = load_config(Path("config/config.example.yaml"))
    assert cfg.symbol == "BTC/USDT"
    assert cfg.timeframe == "1h"
    assert env.BASE_EQUITY == 2000
