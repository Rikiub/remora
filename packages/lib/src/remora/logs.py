"""Remora built-in logger."""

import sys
import uuid
from typing import Literal

from loguru import logger

from remora.constants import LIBRAY_NAME

__all__ = ["LoggingLevels", "disable", "enable", "setup"]

LoggingLevels = Literal[
    "TRACE", "DEBUG", "SUCCESS", "INFO", "WARNING", "ERROR", "CRITICAL"
]


def enable() -> None:
    logger.enable(LIBRAY_NAME)


def disable() -> None:
    logger.disable(LIBRAY_NAME)


def setup(level: LoggingLevels = "DEBUG") -> None:
    enable()

    # Configure logger
    is_verbose = level != "INFO"
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format="<cyan>{time:HH:mm:ss}</cyan> "
        "| <level>{level: <8}</level> "
        "| <level>{message}</level>",
        enqueue=True,
        filter={
            LIBRAY_NAME: "DEBUG" if is_verbose else "INFO",
            "yt-dlp": "WARNING" if is_verbose else False,
        },
    )

    # Add unique ID for the current session
    run_id = str(uuid.uuid4())[:8]
    logger.configure(extra={"run_id": run_id})


disable()
