from loguru import logger
from rich.logging import RichHandler

from remora import logs
from remora.path import get_state_dir
from remora.types import LIBRAY_NAME
from remora_cli.ui.rich import CONSOLE


def setup_logging(level: logs.LoggingLevels) -> None:
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
        filter={
            LIBRAY_NAME: "DEBUG" if is_verbose else "CRITICAL",
            "remora_cli": "DEBUG" if is_verbose else "INFO",
        },
    )

    # Structured Logs
    logger.add(
        get_state_dir() / "logs" / "trace.jsonl",
        level="DEBUG",
        rotation="10 MB",
        serialize=True,
        enqueue=True,
        format=get_format,
        filter={
            LIBRAY_NAME: "DEBUG",
            "remora_cli": "CRITICAL",
        },
    )


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
    is_lib = record["name"].startswith(f"{LIBRAY_NAME}.")

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

    # Lib exclusive prefix
    lib_prefix = ""
    if is_lib:
        lib_prefix = "[dim]\\[LIB] "

    # Format
    return f"{icon} {lib_prefix}{status_prefix}[{color}]{title_prefix}{{message}}[/{color}]"
