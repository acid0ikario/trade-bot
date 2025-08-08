from bot.logger import setup_logger
from pathlib import Path

def test_logger_creates_file(tmp_path: Path):
    logger = setup_logger(tmp_path)
    logger.info("hello")
    # ensure a file appears
    logs = list((tmp_path / "logs").glob("*.log"))
    assert len(logs) >= 1
