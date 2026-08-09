from collections.abc import Iterable

from cyclopts import App, CycloptsError, CycloptsPanel, Parameter
from rich import traceback

from remora_cli.commands.download import download
from remora_cli.commands.extract import extract
from remora_cli.options import DisplayOptions
from remora_cli.ui.help import AppFormatter
from remora_cli.ui.rich import CONSOLE


def create() -> App:
    """Create root app."""
    app = App(
        help="Fishy data extractor/downloader ✨",
        help_format="rich",
        help_formatter=AppFormatter,
        help_on_error=True,
        error_console=CONSOLE,
        default_parameter=Parameter(
            consume_multiple=True,  # Allow pass multiple arguments to a list parameter
        ),
    )

    # Setup Rich Traceback for better debugging experience
    app.register_install_completion_command()
    traceback.install(console=CONSOLE)

    # Init default display options
    DisplayOptions()

    # Create commands
    GROUP = "Subcommands"
    app.command(download, group=GROUP)
    app.command(extract, group=GROUP)

    return app


def run(*tokens: None | str | Iterable[str]):
    """Run app and handle exceptions."""
    app = create()

    try:
        app(*tokens)
    except CycloptsError as e:
        app.error_console.print(CycloptsPanel(e))
        raise SystemExit(1) from e
