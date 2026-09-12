# ruff: noqa: B008

from enum import StrEnum
from typing import Annotated, Literal

from cyclopts import App, Parameter
from loguru import logger

from remora_cli.parameters import DisplayParameters, NetworkParameters, QueryParameter
from remora_cli.parsers import parse_keys, remove_missing
from remora_cli.ui.rich import CONSOLE, Console, smart_print

TABLE_FIELDS_EXCLUDE = {
    "live_status",
    "heatmap",
    "subtitles",
    "chapters",
    "thumbnails",
    "storyboards",
    "streams",
    "fragments",
    "entries",
}
TABLE_FIELDS_ORDER = [
    "excluded_fields",
    "extractor",
    "type",
    "url",
    "id",
    "title",
    "description",
    "duration",
    "live_status",
    "date",
    "creators",
    "uploader",
    "channel",
    "metrics",
    "music",
    "categories",
    "tags",
]


class Panel(StrEnum):
    FORMAT = "Format"


app = App()


@app.command
async def extract(
    query: QueryParameter,
    *,
    format: Annotated[
        Literal["table", "json"] | None,
        Parameter(
            help="Output format of data.",
            short_alias=True,
            group=Panel.FORMAT,
        ),
    ] = None,
    include: Annotated[
        set[str] | None,
        Parameter(
            help="Keys to include.",
            group=Panel.FORMAT,
            negative=False,
        ),
    ] = None,
    exclude: Annotated[
        set[str] | None,
        Parameter(
            help="Keys to exclude.",
            group=Panel.FORMAT,
            negative=False,
        ),
    ] = None,
    # SHARED
    network: NetworkParameters = NetworkParameters(),
    display: DisplayParameters = DisplayParameters(),
):
    "Extract metadata from [green]URL[/] or search [green]service[/]."

    # Lazy startup
    with CONSOLE.status("Starting[blink]...[/]"):
        from rich.json import JSON

        from remora.extractor import MediaExtractor
        from remora_cli.ui.extractor import dict_to_table, extract_queries

        console = Console()
        extractor = MediaExtractor(network.build_options())

    # Determine user intent
    sel_format = format
    if not format:
        sel_format = "table" if console.is_terminal else "json"

    # Filters
    sel_include = parse_keys(include or {})
    sel_exclude = parse_keys(exclude or {})

    if sel_format == "table" and not sel_include:
        sel_exclude |= TABLE_FIELDS_EXCLUDE

    for key in sel_include:
        sel_exclude.discard(key)

    # Extract queries
    async for _, result in extract_queries(query, extractor.network_options):
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
            data = remove_missing({"excluded_fields": sel_exclude} | data)

            sorted_data = {k: data[k] for k in TABLE_FIELDS_ORDER if k in data}
            sorted_data |= data
            table = dict_to_table(sorted_data)

            if console.is_terminal:
                smart_print(table)
            else:
                console.print(table)
