from enum import StrEnum
from typing import Annotated, Literal

from cyclopts import App, Parameter
from loguru import logger

from remora_cli.options import DisplayOptions, NetworkOptions, QueryParameter
from remora_cli.parsers import parse_keys, remove_missing
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
    display: DisplayOptions | None = None,
    auth: NetworkOptions | None = None,
):
    "Extract metadata from [green]URL[/] or search [green]service[/]."

    display = display or DisplayOptions()
    auth = auth or NetworkOptions()

    # Lazy startup
    with CONSOLE.status("Starting[blink]...[/]"):
        from rich.json import JSON

        from remora import MediaExtractor
        from remora import NetworkOptions as Network
        from remora.models.cookies import CookieList
        from remora_cli.ui.extractor import dict_to_table, extract_queries

        console = Console()
        extractor = MediaExtractor(
            Network(
                cookies=CookieList.from_file(auth.cookies) if auth.cookies else None,
                proxy=auth.proxy,
                impersonate=auth.impersonate,
            )
        )

    # Determine user intent
    sel_format = format
    if not format:
        sel_format = "table" if console.is_terminal else "json"

    # Filters
    sel_include = parse_keys(include or {})
    sel_exclude = parse_keys(exclude or {})

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
