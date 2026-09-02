"""Reusable option groups shared across commands."""

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from cyclopts import Parameter, validators

from remora.logs import LoggingLevels
from remora.models import (
    CookieList,
    ImpersonateClient,
    SearchService,
    validate_impersonate_target,
)
from remora.models import NetworkOptions as Network

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


@Parameter(name="*", group="Display")
@dataclass(slots=True)
class DisplayOptions:
    """Commons options for the display of logs and visuals."""

    quiet: Annotated[
        bool,
        Parameter(
            help="Supress screen information.",
            negative=False,
        ),
    ] = False
    verbose: Annotated[
        bool,
        Parameter(
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


@Parameter(name="*", group="Network")
@dataclass(slots=True)
class NetworkOptions:
    """Commons network options."""

    cookies: Annotated[
        Path | None,
        Parameter(
            help="Path to a cookies file.",
            validator=validators.Path(
                exists=True,
                file_okay=True,
                dir_okay=False,
                ext=["txt", "json"],
            ),
        ),
    ] = None
    proxy: Annotated[
        str | None,
        Parameter(help="HTTP/HTTPS/SOCKS5 proxy URL."),
    ] = None
    impersonate: Annotated[
        ImpersonateClient | str | None,
        Parameter(
            help="Target browser to impersonate.",
            validator=lambda type, v: validate_impersonate_target(v) if v else None,
        ),
    ] = None

    def build_options(self) -> Network:
        # Init options
        network = Network(
            cookies=CookieList.from_file(self.cookies) if self.cookies else None,
            proxy=self.proxy,
        )

        # Replace directly to avoid trigger validation again
        network.impersonate = self.impersonate

        # Return validated options
        return network
