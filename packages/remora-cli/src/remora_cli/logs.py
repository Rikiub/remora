import uuid
from functools import partial

from loguru import logger
from rich.logging import RichHandler
from rich.text import Text

import remora
import remora_cli
from remora import logs
from remora.logs import LoggingLevels
from remora.path import get_log_dir
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
            remora_cli.__name__: "DEBUG" if is_verbose else "INFO",
            remora.__name__: "DEBUG" if is_verbose else False,
            "yt-dlp": "WARNING" if is_verbose else False,
        },
    )

    # Structured Logs
    logger.add(
        get_log_dir() / "remora.jsonl",
        level="DEBUG",
        retention=1,
        rotation="10 MB",
        compression="zip",
        serialize=True,
        enqueue=True,
        format=partial(get_format, markup=False, lib_only=True),
        filter={
            remora.__name__: "DEBUG",
            "yt-dlp": "WARNING",
            remora_cli.__name__: False,
        },
    )

    # Add unique ID for the current session
    run_id = str(uuid.uuid4())[:8]
    logger.configure(extra={"run_id": run_id})


LEVEL_STYLE: dict[LoggingLevels, str] = {
    "DEBUG": "cyan",
    "SUCCESS": "khaki1",
    "INFO": "khaki1",
    "WARNING": "yellow italic",
    "ERROR": "bright_red",
    "CRITICAL": "bold white on red",
}


def get_format(record, markup: bool = True, lib_only: bool = False) -> str:
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
    color = LEVEL_STYLE.get(level.name, "white")

    # Module prefix
    is_lib = record["name"].startswith(f"{remora.__name__}.")
    is_ydl = record["name"] == "yt-dlp"
    module_prefix = ""

    if not lib_only and is_lib:
        module_prefix = "[dim]\\[LIB] "
    if is_ydl:
        module_prefix = "[dim]\\[YDL] "

    # Format
    message = f"{icon} {module_prefix}{status_prefix}[{color}]{title_prefix}{{message}}[/{color}]"
    return message if markup else Text.from_markup(message).plain
