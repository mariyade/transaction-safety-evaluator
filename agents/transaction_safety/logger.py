import logging
import os
from datetime import datetime
from pathlib import Path

_log_file: Path | None = None


def _get_log_file() -> Path:
    """Return the log file path for this process, creating it once per run."""
    global _log_file
    if _log_file is None:
        log_dir = Path(os.getenv("LOG_DIR", "logs"))
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _log_file = log_dir / f"agent_{timestamp}.log"
    return _log_file


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Call with get_logger(__name__) in each module."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        level_name = os.getenv("LOG_LEVEL", "INFO").upper()
        level = getattr(logging, level_name, logging.INFO)
        logger.setLevel(level)

        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        )

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        file_handler = logging.FileHandler(_get_log_file())
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        logger.propagate = False

    return logger
