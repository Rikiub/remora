from enum import StrEnum
from pathlib import Path
from typing import Annotated

from typer import Option, Typer

from remora_cli.config import CONFIG


def show_version(show: bool) -> None:
    if show:
        from importlib.metadata import version

        print(version(Path(__file__).parent.parent.name))

        raise SystemExit()


class HelpPanel(StrEnum):
    DISPLAY = "Display"
    EXTRACTION = "Extraction"


app = Typer()


@app.command()
def main(
    quiet: Annotated[
        bool,
        Option(
            "--quiet",
            help="Supress screen information.",
            rich_help_panel=HelpPanel.DISPLAY,
        ),
    ] = CONFIG.quiet,
    verbose: Annotated[
        bool,
        Option(
            "--verbose",
            help="Display more information on screen.",
            rich_help_panel=HelpPanel.DISPLAY,
        ),
    ] = CONFIG.verbose,
    version: Annotated[
        bool,
        Option(
            "--version",
            help="Show current version and exit.",
            rich_help_panel=HelpPanel.DISPLAY,
            callback=show_version,
            is_eager=True,
        ),
    ] = False,
    cache: Annotated[
        bool,
        Option(
            help="Process using cache.",
            rich_help_panel=HelpPanel.EXTRACTION,
        ),
    ] = False,
):
    """Fishy data extractor/downloader ✨"""

    CONFIG.verbose = verbose
    CONFIG.quiet = quiet
    CONFIG.cache = cache

    # Setup logger
    from remora_cli.logs import setup_logging

    setup_logging(CONFIG.log_level)
