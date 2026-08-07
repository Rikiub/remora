from enum import StrEnum
from typing import Annotated

from cyclopts import App, Parameter

from remora_cli.config import CONFIG
from remora_cli.ui.help import TyperFormatter


class HelpPanel(StrEnum):
    DISPLAY = "Display"


def create_app() -> App:
    from remora_cli.commands import download, extract

    app = App(
        name="remora",
        help="Fishy data extractor/downloader ✨",
        help_format="rich",
        help_formatter=TyperFormatter,
        help_on_error=True,
    )

    app.command(download.app, name="*")
    app.command(extract.app, name="*")

    @app.meta.default
    def launcher(
        quiet: Annotated[
            bool,
            Parameter(
                group=HelpPanel.DISPLAY,
                help="Supress screen information.",
            ),
        ] = CONFIG.quiet,
        verbose: Annotated[
            bool,
            Parameter(
                group=HelpPanel.DISPLAY,
                help="Display more information on screen.",
            ),
        ] = CONFIG.verbose,
    ):
        CONFIG.quiet = quiet
        CONFIG.verbose = verbose

        # Setup logger
        from remora_cli.logs import setup_logging

        setup_logging(CONFIG.log_level)

        return app()

    return app
