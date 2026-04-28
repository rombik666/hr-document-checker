import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rag_code.config import LOGS_DIR

LOGGER_NAME = "rag_code"


def setup_logging(log_level: str = "INFO") -> None:
    root_logger = logging.getLogger(LOGGER_NAME)

    if root_logger.handlers:
        return

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(level)
    root_logger.propagate = False

    log_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(log_format)

    app_file_handler = RotatingFileHandler(
        filename=LOGS_DIR / "app.log",
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    app_file_handler.setLevel(level)
    app_file_handler.setFormatter(log_format)

    error_file_handler = RotatingFileHandler(
        filename=LOGS_DIR / "errors.log",
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(log_format)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(app_file_handler)
    root_logger.addHandler(error_file_handler)


def get_logger(module_name: str) -> logging.Logger:
    return logging.getLogger(f"{LOGGER_NAME}.{module_name}")