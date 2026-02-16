import logging

from loguru import logger
from rich.logging import RichHandler

from remora.types import APP_NAME, LoggingLevels
from remora_cli.ui.rich import CONSOLE


class ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)

        match record.levelno:
            case logging.DEBUG:
                color = "[blue]"
            case logging.INFO:
                color = "[khaki1]"
            case logging.WARNING:
                color = "[yellow][italic]"
            case logging.ERROR:
                color = "[red]"
            case logging.CRITICAL:
                color = "[bold red]"
            case _:
                color = ""

        return color + message


def start_logger(level: LoggingLevels):
    if level == "INFO":
        verbose = False
    else:
        verbose = True

    rich_handler = RichHandler(
        level=level,
        show_level=verbose,
        show_time=verbose,
        show_path=verbose,
        markup=True,
        console=CONSOLE,
    )
    rich_handler.setFormatter(ColorFormatter())

    logger.remove()
    logger.add(
        rich_handler,
        level=level,
        format="{message}",
        backtrace=False,
    )

    logger.enable(APP_NAME)
