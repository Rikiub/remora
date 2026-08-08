"""Reusable option groups shared across commands."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated

from cyclopts import Parameter

from remora.logs import LoggingLevels


class OptionsPanel(StrEnum):
    DISPLAY = "Display"
    AUTH = "Authentication"


QueryParameter = Annotated[
    list[str],
    Parameter(
        help="""[green]URLs[/] and [green]queries[/] to process.
- Insert a [green]URL[/] to process.
- Insert a [green]service[/] and [green]query[/] to search and process.
""",
        show_default=False,
    ),
]


@Parameter(name="*")
@dataclass(slots=True)
class DisplayOptions:
    quiet: Annotated[
        bool,
        Parameter(
            group=OptionsPanel.DISPLAY,
            help="Supress screen information.",
        ),
    ] = False
    verbose: Annotated[
        bool,
        Parameter(
            group=OptionsPanel.DISPLAY,
            help="Display more information on screen.",
        ),
    ] = False

    @property
    def log_level(self) -> LoggingLevels:
        if self.quiet:
            return "CRITICAL"
        elif self.verbose:
            return "DEBUG"
        else:
            return "INFO"

    def __post_init__(self):
        from remora_cli.logs import setup_logging

        setup_logging(self.log_level)


@Parameter(name="*")
@dataclass(slots=True)
class AuthOptions:
    """Commons authentication options for every command."""

    cookies: Annotated[
        str | None,
        Parameter(
            help="Browser name or path to a [green]cookies.txt[/] file.",
            group=OptionsPanel.AUTH,
        ),
    ] = None
    proxy: Annotated[
        str | None,
        Parameter(
            help="HTTP/HTTPS/SOCKS5 proxy [green]URL[/].",
            group=OptionsPanel.AUTH,
        ),
    ] = None
