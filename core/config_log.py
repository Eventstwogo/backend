
import os
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from colorlog import ColoredFormatter
from pythonjsonlogger import jsonlogger


def setup_logging() -> None:
    """Configures logging based on the environment (local vs cloud/docker)."""

    # Detect environment (local vs cloud/docker)
    env = os.getenv("APP_ENV", "local").lower()  # "local" or "cloud"
    log_dir = "logs"

    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"api_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = TimedRotatingFileHandler(
        filename=log_file, when="midnight", interval=1, backupCount=7, encoding="utf-8"
    )

    if env == "local":
        # Color logs for local development
        log_format = (
            "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s | "
            "%(filename)s:%(lineno)d | %(funcName)s() | %(message)s%(reset)s"
        )
        color_formatter = ColoredFormatter(
            log_format,
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
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler.setFormatter(file_formatter)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(color_formatter)

    else:
        # JSON logs for cloud/docker
        json_formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(filename)s %(lineno)d",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        file_handler.setFormatter(json_formatter)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(json_formatter)

    # Root logger config
    logging.basicConfig(
        level=logging.DEBUG if env == "local" else logging.INFO,
        handlers=[file_handler, console_handler],
    )

    # Optional: silence noisy loggers (like uvicorn's access logs)
    logging.getLogger("uvicorn.access").disabled = True

    logging.info(f"Logging initialized for environment: {env.upper()}")
