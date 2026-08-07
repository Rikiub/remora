from enum import StrEnum
from typing import Annotated, Literal

from loguru import logger
from typer import Argument, BadParameter, Option, Typer

from remora_cli.completions import complete_query, complete_template_key
from remora_cli.helpers import make_async, remove_missing
from remora_cli.ui.rich import CONSOLE, Console, smart_print

DEFAULT_EXCLUDE = {
    "streams",
    "live_status",
    "subtitles",
    "chapters",
    "thumbnails",
    "heatmap",
    "medias",
    "playlists",
    "is_cache",
}
FIELDS_ORDER = [
    "type",
    "url",
    "id",
    "extractor",
    "title",
    "description",
    "live_status",
    "duration",
    "upload_date",
    "modified_date",
    "release_date",
    "uploader",
    "channel",
    "metrics",
    "music",
    "categories",
    "tags",
]


def parse_keys(value: list[str]) -> list[str]:
    if value:
        from remora._internal.template.key import validate_key
        from remora.exceptions import OutputTemplateError

        results = []

        for item in value:
            # Split by comma and strip whitespace
            keys = [k.strip() for k in item.split(",") if k.strip()]

            for key in keys:
                try:
                    validate_key(key, True)
                    results.append(key)
                except OutputTemplateError as e:
                    raise BadParameter(str(e))
        return results
    return value


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
            - Insert a [green]URL[/] to extract.\n
            - Insert a [green]service[/] and [green]query[/] to search and extract.
            """,
            show_default=False,
            autocompletion=complete_query,
        ),
    ],
    format: Annotated[
        Literal["table", "json"] | None,
        Option(
            "--format",
            "-f",
            help="Output format of data.",
            rich_help_panel=HelpPanel.FORMAT,
        ),
    ] = None,
    include: Annotated[
        list[str],
        Option(
            help="Keys to include.",
            rich_help_panel=HelpPanel.FORMAT,
            autocompletion=complete_template_key,
            callback=parse_keys,
        ),
    ] = [],  # noqa: B006
    exclude: Annotated[
        list[str],
        Option(
            help="Keys to exclude.",
            rich_help_panel=HelpPanel.FORMAT,
            autocompletion=complete_template_key,
            callback=parse_keys,
        ),
    ] = [],  # noqa: B006
):
    """Extract metadata from [green]URL[/] or search [green]service[/]."""

    # Lazy startup
    with CONSOLE.status("Starting[blink]...[/]"):
        from rich.json import JSON

        from remora import MediaExtractor
        from remora_cli.ui.extractor import dict_to_table, extract_queries

        console = Console()
        extractor = MediaExtractor()

    # Determine user intent
    sel_format = format
    if not format:
        sel_format = "table" if console.is_terminal else "json"

    # Filters
    sel_include = set(include)
    sel_exclude = set(exclude)

    if sel_format == "table" and not sel_include:
        sel_exclude |= DEFAULT_EXCLUDE

    for key in sel_include:
        sel_exclude.discard(key)

    # Extract queries
    async for _, result in extract_queries(query, extractor):
        logger.success("Successful extraction")

        # Show
        if sel_format == "json":
            data = result.model_dump_json(
                include=sel_include or None,
                exclude=sel_exclude or None,
            )

            if console.is_terminal:
                smart_print(JSON(data))
            else:
                print(data)

        elif sel_format == "table":
            data = result.model_dump(
                include=sel_include or None,
                exclude=sel_exclude or None,
                exclude_none=True,
                mode="json",
            )
            data = remove_missing(data)

            sorted_data = {k: data[k] for k in FIELDS_ORDER if k in data}
            sorted_data |= data
            table = dict_to_table(sorted_data)

            if console.is_terminal:
                smart_print(table)
            else:
                console.print(table)
