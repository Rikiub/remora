from cyclopts import CycloptsError, CycloptsPanel

from remora_cli.ui.rich import CONSOLE


def run() -> None:
    from importlib.metadata import version

    from remora_cli.commands.main import create_app

    app = create_app(version=version("remora-cli"))

    try:
        app.meta()
    except CycloptsError as error:
        CONSOLE.print(CycloptsPanel(error))
        raise SystemExit(1) from error