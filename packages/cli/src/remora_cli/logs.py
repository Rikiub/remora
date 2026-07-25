from loguru import logger
from rich.logging import RichHandler

from remora import logs
from remora_cli.ui.rich import CONSOLE


def setup_logging(level: logs.LoggingLevels):
    logs.enable()

    is_verbose = level != "INFO"

    rich_handler = RichHandler(
        level=level,
        show_level=is_verbose,
        show_time=is_verbose,
        show_path=is_verbose,
        console=CONSOLE,
        markup=True,
        rich_tracebacks=True,
    )

    logger.remove()
    logger.add(
        rich_handler,
        level=level,
        backtrace=False,
        enqueue=True,
        format=get_format,
        filter=remora_only_debug,
    )

    # Structured Logs
    """
    format = (
        "<cyan>{time:HH:mm:ss}</cyan> "
        + "| <level>{level: <8}</level> "
        + "| <level>{message}</level>"
    )

    logger.add(
        "logs/trace.jsonl",
        level="DEBUG",
        rotation="10 MB",
        serialize=True,
        enqueue=True,
        format=format,
        filter={
            "remora_cli": "CRITICAL",
            "remora": "DEBUG",
        },
    )
    """


LEVEL_COLORS: dict[logs.LoggingLevels, str] = {
    "DEBUG": "blue",
    "SUCCESS": "khaki1",
    "INFO": "khaki1",
    "WARNING": "yellow italic",
    "ERROR": "red",
    "CRITICAL": "bold red",
}


def get_format(record) -> str:
    level = record["level"]
    extra = record.get("extra", {})
    icon = extra.get("icon") or getattr(record["level"], "icon", "")

    # Prefixes
    status_prefix = ""
    if (
        level.name == "DEBUG"
        and (media_id := extra.get("media_id"))
        and (status := extra.get("status"))
    ):
        status_prefix = f"[[dim]{media_id}[/]] [bold]{status.upper():<11}[/] | "

    title_prefix = ""
    if level.name != "DEBUG" and (title := extra.get("media_title")):
        title_prefix = f'"{title}" '

    # Colors
    color = LEVEL_COLORS.get(level.name, "white")

    # Format
    return f"{icon} {status_prefix}[{color}]{title_prefix}{{message}}[/{color}]"


def remora_only_debug(record):
    is_remora = record["name"].startswith("remora.")
    is_debug = record["level"].name == "DEBUG"
    return is_remora and not is_debug
