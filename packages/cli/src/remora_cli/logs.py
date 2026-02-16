from loguru import logger
from rich.logging import RichHandler

from remora import logs
from remora_cli.ui.rich import CONSOLE


def setup_logging(level: logs.LoggingLevels):
    logs.enable()

    if level == "INFO":
        verbose = False
    else:
        verbose = True

    rich_handler = RichHandler(
        level=level,
        show_level=verbose,
        show_time=verbose,
        show_path=False,
        markup=True,
        console=CONSOLE,
    )

    logger.remove()
    logger.add(
        rich_handler,
        level=level,
        format=get_format,
        backtrace=False,
    )


def get_format(record) -> str:
    level: logs.LoggingLevels = record["level"].name  # type: ignore

    # Colors
    colors: dict[logs.LoggingLevels, str] = {
        "DEBUG": "[blue]",
        "INFO": "[khaki1]",
        "WARNING": "[yellow][italic]",
        "ERROR": "[red]",
        "CRITICAL": "[bold red]",
    }
    color = colors.get(level)

    extra: dict[str, str] = record.get("extra", {})
    status = extra.get("status", "")
    media_id = extra.get("media_id", "")

    prefix = ""
    if status and media_id:
        prefix = f"[[dim]{media_id}[/]] [bold]{status.upper():<11}[/] | "

    # Message Format
    return f"{prefix}{color}{{message}}[/]"
