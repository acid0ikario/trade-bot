from __future__ import annotations
from loguru import logger
from pathlib import Path


def setup_logger(data_dir: str | Path = "data"):
    data_path = Path(data_dir)
    logs_path = data_path / "logs"
    logs_path.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(lambda msg: print(msg, end=""))
    logger.add(
        logs_path / "runtime.log",
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        enqueue=True,
    )
    return logger
