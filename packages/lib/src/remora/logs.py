"""
Remora default logger.
Disabled by default.
"""

from typing import Literal

from loguru import logger

from remora.types import APP_NAME

LoggingLevels = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def enable():
    logger.enable(APP_NAME)


def disable():
    logger.disable(APP_NAME)


def setup(level: LoggingLevels = "INFO") -> None:
    enable()

    import sys

    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format=get_format,
    )


def get_format(record) -> str:
    # Extract variables
    extra = record.get("extra", {})
    media_id: str = extra.get("media_id", "")
    status: str = extra.get("status", "")

    # Format
    return f"[{media_id}] {status.upper()} | {{message}}"


disable()
