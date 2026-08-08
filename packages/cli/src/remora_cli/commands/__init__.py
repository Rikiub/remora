from cyclopts import App, Parameter


def create_app() -> App:
    from remora_cli.commands.download import download
    from remora_cli.commands.extract import extract
    from remora_cli.ui.help import AppFormatter
    from remora_cli.ui.rich import CONSOLE

    app = App(
        name="remora",
        help="Fishy data extractor/downloader ✨",
        help_format="rich",
        help_formatter=AppFormatter,
        help_on_error=True,
        error_console=CONSOLE,
        default_parameter=Parameter(
            allow_leading_hyphen=True,
        ),
    )

    GROUP = "Subcommands"
    app.command(download, group=GROUP)
    app.command(extract, group=GROUP)

    return app
