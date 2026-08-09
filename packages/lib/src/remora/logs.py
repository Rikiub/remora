"""
Remora default logger.
Disabled by default.
"""

from typing import Literal

from loguru import logger

from remora.types import LIBRAY_NAME

__all__ = ["LoggingLevels", "disable", "enable", "setup"]

LoggingLevels = Literal["DEBUG", "SUCCESS", "INFO", "WARNING", "ERROR", "CRITICAL"]


def enable() -> None:
    logger.enable(LIBRAY_NAME)


def disable() -> None:
    logger.disable(LIBRAY_NAME)


def setup(level: LoggingLevels = "DEBUG") -> None:
    enable()

    import sys

    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format="<cyan>{time:HH:mm:ss}</cyan> "
        "| <level>{level: <8}</level> "
        "| <level>{message}</level>",
        enqueue=True,
    )


disable()
