from enum import StrEnum
from typing import Annotated, Literal

from loguru import logger
from remora_cli.completions import complete_query, complete_template_key
from remora_cli.config import CONFIG
from remora_cli.helpers import make_async
from remora_cli.ui.rich import Console, Status
from typer import Argument, Option, Typer


class HelpPanel(StrEnum):
    FORMAT = "Format"


app = Typer()


@app.command(no_args_is_help=True)
@make_async
async def extract(
    query: Annotated[
        list[str],
        Argument(
            help="""[green]URLs[/] and [green]queries[/] to process.
            \n
            - Insert a [green]URL[/] to extract. [grey62](Default)[/]\n
            - Select a [green]SERVICE[/] to search and extract.
            """,
            show_default=False,
            autocompletion=complete_query,
            metavar="URL | SERVICE",
        ),
    ],
    format: Annotated[
        Literal["table", "json"],
        Option(
            help="Output format of data.",
            rich_help_panel=HelpPanel.FORMAT,
        ),
    ] = "table",
    include: Annotated[
        list[str],
        Option(
            help="Keys to include.",
            rich_help_panel=HelpPanel.FORMAT,
            autocompletion=complete_template_key,
        ),
    ] = [],
    exclude: Annotated[
        list[str],
        Option(
            help="Keys to exclude.",
            rich_help_panel=HelpPanel.FORMAT,
            autocompletion=complete_template_key,
        ),
    ] = [],
):
    """Extract metadata from [green]URL[/] or search [green]SERVICE[/]."""

    # Lazy Import
    with Status("Starting[blink]...[/]"):
        from remora.extractor import MediaExtractor
        from remora_cli.ui.extractor import extract_queries, dict_to_table
        from rich.json import JSON

    console = Console()
    extractor = MediaExtractor(use_cache=CONFIG.cache)

    default_exclude = {
        "streams",
        "subtitles",
        "chapters",
        "thumbnails",
        "heatmap",
        "medias",
        "playlists",
        "entries",
    }
    default_exclude = {*exclude, *default_exclude}

    for key in include:
        default_exclude.discard(key)

    async for result in extract_queries(query, extractor):
        if result.type == "media" and result.is_cache:
            logger.info("Data extracted from cache.")
        else:
            logger.info("Successful extraction.")

        if not console.is_terminal or format == "json":
            data = result.model_dump_json(
                include={*include} or None,
                exclude=default_exclude or None,
            )

            if console.is_terminal:
                data = JSON(data)
                console.print(data)
            else:
                print(data)
        elif format == "table":
            data = result.model_dump(
                include={*include} or None,
                exclude=default_exclude or None,
            )
            table = dict_to_table(data)
            console.print(table)
