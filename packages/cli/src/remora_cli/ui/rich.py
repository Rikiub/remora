"""Custom `Rich` classes."""

import os
from typing import Any

from rich.console import Console, RenderableType
from rich.status import Status as _Status

from remora_cli.config import CONFIG

CONSOLE = Console(stderr=True)


class Status(_Status):
    def __init__(self, status: RenderableType):
        self.disable = CONFIG.quiet
        super().__init__(status, console=CONSOLE)

    def start(self) -> None:
        if not self.disable:
            return super().start()

    def stop(self) -> None:
        if not self.disable:
            return super().stop()


def smart_print(
    content: Any,
    pager: bool = True,
    console: Console = Console(force_terminal=True),
):
    """Catch output and send to system pager if content is too long.

    By default will set environment variables to ensure system pager can process colors.

    If pager fails, then will just print the content.
    """

    # Set colors in LESS pager (common in Linux)
    os.environ["LESS"] = "-RF"

    if pager:
        with console.pager(styles=True):
            console.print(content)
    else:
        console.print(content)
