from pathlib import Path
from typing import Annotated

from remora_cli.config import CONFIG
from typer import Option, Typer


def show_version(show: bool) -> None:
    if show:
        from importlib.metadata import version

        print(version(Path(__file__).parent.parent.name))

        raise SystemExit()


app = Typer()
PANEL = "Display"


@app.command()
def main(
    quiet: Annotated[
        bool,
        Option(
            "--quiet",
            help="Supress screen information.",
            rich_help_panel=PANEL,
        ),
    ] = CONFIG.quiet,
    verbose: Annotated[
        bool,
        Option(
            "--verbose",
            help="Display more information on screen.",
            rich_help_panel=PANEL,
        ),
    ] = CONFIG.verbose,
    version: Annotated[
        bool,
        Option(
            "--version",
            help="Show current version and exit.",
            rich_help_panel=PANEL,
            callback=show_version,
            is_eager=True,
        ),
    ] = False,
):
    """Download any video/audio you want from a simple URL ✨"""

    CONFIG.verbose = verbose
    CONFIG.quiet = quiet

    # Setup logger
    from remora_cli.logger import start_logger

    start_logger(CONFIG.log_level)
