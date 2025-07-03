# core/logging_config.py

import logging
import os
from datetime import datetime
from logging import Logger, StreamHandler
from logging.handlers import TimedRotatingFileHandler

from pythonjsonlogger.json import JsonFormatter

# === Logging Setup Configuration ===
APPLICATION_NAME = os.getenv("APP_NAME", "Shoppersky App API").replace(" ", "_")
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE_PATH = os.path.join(
    LOG_DIR,
    f"{APPLICATION_NAME}_{datetime.now().strftime('%Y%m%d')}.log",
)


# === Reusable Logger Factory ===
def get_logger(name: str) -> Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # Prevent duplicate handlers

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))

    # JSON formatter for structured logs
    formatter = JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d"
    )

    # Console Handler
    console_handler = StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # File Handler with daily rotation
    file_handler = TimedRotatingFileHandler(
        filename=LOG_FILE_PATH, when="midnight", backupCount=7, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.propagate = False  # Prevent duplicate logs in root

    return logger


