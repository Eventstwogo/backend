# core/logging_config.py

# core/logging_config.py

import logging
import os
from datetime import datetime
from logging import Logger, StreamHandler
from logging.handlers import TimedRotatingFileHandler

from colorlog import ColoredFormatter
from pythonjsonlogger.json import JsonFormatter

# Import settings to use the correct environment
from core.config import settings

# === Environment Configuration ===
ENVIRONMENT = settings.ENVIRONMENT.lower()
APPLICATION_NAME = settings.APP_NAME.replace(" ", "_")
LOG_LEVEL = settings.LOG_LEVEL.upper()

# === File Path Setup ===
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE_PATH = os.path.join(
    LOG_DIR, f"{APPLICATION_NAME}_{datetime.now().strftime('%Y%m%d')}.log"
)

# Flag to track if initialization message has been logged
_INIT_MESSAGE_LOGGED = False


# === Logger Factory Function ===
def get_logger(name: str) -> Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # Avoid adding handlers multiple times

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))

    # === Formatter Configuration ===
    if ENVIRONMENT == "development":
        # Local: Human-readable and colored
        console_formatter = ColoredFormatter(
            "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s | "
            "%(filename)s:%(lineno)d | %(funcName)s() | %(message)s%(reset)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            reset=True,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )

        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        # Cloud: JSON structure
        console_formatter = JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_formatter = console_formatter

    # === Console Handler ===
    console_handler = StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(console_formatter)

    # === File Handler with Daily Rotation ===
    file_handler = TimedRotatingFileHandler(
        filename=LOG_FILE_PATH,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # === Add Handlers ===
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False  # Prevent duplicate logs in root

    # Optional: disable noisy loggers
    logging.getLogger("uvicorn.access").disabled = True

    # Log initialization message only once at application startup
    global _INIT_MESSAGE_LOGGED
    if not _INIT_MESSAGE_LOGGED:
        logger.info(
            f"Logging initialized for environment: {ENVIRONMENT.upper()}"
        )
        _INIT_MESSAGE_LOGGED = True

    return logger
