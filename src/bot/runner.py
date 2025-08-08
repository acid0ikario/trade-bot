from __future__ import annotations
import argparse
from pathlib import Path

from .logger import setup_logger
from .config import load_config
from .notifier import Notifier


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", action="store_true", help="Run in paper mode")
    parser.add_argument("--config", type=str, default="config/config.yaml")
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
        f"paper={args.paper}"
    )
    logger.info(banner)
    notifier.send(banner)

    logger.info("Runner stub complete. Next: implement exchange + risk + strategy.")


if __name__ == "__main__":
    main()
