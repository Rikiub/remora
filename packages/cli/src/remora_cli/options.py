"""Reusable option groups shared across commands."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from remora.logs import LoggingLevels
from remora.models.search import SearchService


class OptionsPanel(StrEnum):
    DISPLAY = "Display"
    EXTRACTOR = "Extractor"


QueryParameter = Annotated[
    list[str | SearchService],
    Parameter(
        help="""[green]URLs[/] and [green]queries[/] to process.
- Insert a [green]URL[/] to process.
- Insert a [green]service[/]:[green]query[/] to search and process.
""",
        negative=False,
    ),
]


@Parameter(name="*")
@dataclass(slots=True)
class DisplayOptions:
    """Commons options for the display of logs and visuals."""

    quiet: Annotated[
        bool,
        Parameter(
            group=OptionsPanel.DISPLAY,
            help="Supress screen information.",
            negative=False,
        ),
    ] = False
    verbose: Annotated[
        bool,
        Parameter(
            group=OptionsPanel.DISPLAY,
            help="Display more information on screen.",
            negative=False,
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


@Parameter(name="*", group=OptionsPanel.EXTRACTOR)
@dataclass(slots=True)
class ExtractorOptions:
    """Commons authentication options for specific commands."""

    cookies: Annotated[
        Path | None,
        Parameter(help="Path to a [green]cookies.txt[/] file."),
    ] = None
    proxy: Annotated[
        str | None,
        Parameter(help="HTTP/HTTPS/SOCKS5 proxy [green]URL[/]."),
    ] = None
    impersonate: Annotated[
        str | None,
        Parameter(help="Target browser to impersonate."),
    ] = None
