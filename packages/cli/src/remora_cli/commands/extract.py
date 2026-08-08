from enum import StrEnum
from typing import Annotated, Literal

from cyclopts import App, CycloptsError, Parameter
from loguru import logger

from remora_cli.helpers import remove_missing
from remora_cli.options import AuthOptions, QueryParameter
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
                    raise CycloptsError(str(e))
        return results
    return value


class HelpPanel(StrEnum):
    FORMAT = "Format"


app = App(
    name="*",
    help="Extract metadata from [green]URL[/] or search [green]service[/].",
)


@app.command
async def extract(
    query: QueryParameter,
    /,
    format: Annotated[
        Literal["table", "json"] | None,
        Parameter(
            name=["--format", "-f"],
            help="Output format of data.",
            group=HelpPanel.FORMAT,
        ),
    ] = None,
    include: Annotated[
        list[str] | None,
        Parameter(
            help="Keys to include.",
            group=HelpPanel.FORMAT,
        ),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        Parameter(
            help="Keys to exclude.",
            group=HelpPanel.FORMAT,
        ),
    ] = None,
    # AUTH
    auth: AuthOptions | None = None,
):
    """Extract metadata from URL or search service."""

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
    sel_include = set(parse_keys(include or []))
    sel_exclude = set(parse_keys(exclude or []))

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
