"""Custom `Rich` classes."""

import os
from typing import Any

from rich.console import Console

CONSOLE = Console(stderr=True)


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
