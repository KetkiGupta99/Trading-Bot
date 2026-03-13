"""
Logging configuration for the trading bot.
Sets up both file and console handlers with structured formatting.
"""

import logging
import os
from datetime import datetime


def setup_logging(log_dir: str = "logs", log_level: int = logging.DEBUG) -> logging.Logger:
    """
    Configure and return the root logger for the trading bot.

    Args:
        log_dir: Directory where log files will be stored.
        log_level: Logging level (default: DEBUG for file, INFO for console).

    Returns:
        Configured logger instance.
    """
    os.makedirs(log_dir, exist_ok=True)

    log_filename = os.path.join(log_dir, f"trading_bot_{datetime.utcnow().strftime('%Y%m%d')}.log")

    logger = logging.getLogger("trading_bot")
    logger.setLevel(log_level)

    # Avoid duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )

    # File handler — captures everything (DEBUG+)
    fh = logging.FileHandler(log_filename, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Console handler — only INFO+ to keep CLI output clean
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.debug("Logging initialised. Log file: %s", log_filename)
    return logger