from collections.abc import AsyncIterable

from loguru import logger
from rich import box
from rich.highlighter import ReprHighlighter
from rich.table import Table
from typer import Exit

from remora import MediaExtractor
from remora.exceptions import RemoraError
from remora.models.media.list import SearchList
from remora.models.media.types import ExtractResult
from remora_cli.completions import parse_queries
from remora_cli.ui.rich import Status


async def extract_queries(
    queries: list[str],
    extractor: MediaExtractor,
) -> AsyncIterable[ExtractResult | SearchList]:
    for target, entry in parse_queries(queries):
        try:
            with Status("Searching[blink]...[/]"):
                if target == "url":
                    logger.info('🔎 Extract URL: "{url}"', url=entry)
                    result = await extractor.extract(entry)

                    if result.type == "playlist":
                        logger.info('🔎 Playlist title: "{title}"', title=result.title)

                else:
                    logger.info(
                        '🔎 Search from {extractor}: "{query}"',
                        extractor=target,
                        query=entry,
                    )

                    result = await extractor.extract_search(entry, target)

                    if not result.medias:
                        logger.warning("❗ No results found")
                        raise Exit()
            yield result
        except RemoraError as error:
            logger.error("❌ {error}", error=str(error))
        finally:
            logger.info("")


hlt = ReprHighlighter()


def dict_to_table(data: dict) -> Table:
    table = Table(title=None, show_header=False, box=box.ROUNDED)
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value")

    for key, value in data.items():
        if isinstance(value, dict):
            table.add_row(key, gen_table(value))
        elif isinstance(value, list):
            table.add_row(key, gen_list_output(value))
        else:
            table.add_row(key, hlt(str(value)))

    return table


def gen_table(data: dict) -> Table:
    table = Table(show_header=False, box=box.ROUNDED, padding=(0, 1))
    table.add_column("K", style="bold yellow", no_wrap=True)
    table.add_column("V")

    for k, v in data.items():
        if isinstance(v, dict):
            table.add_row(k, gen_table(v))
        elif isinstance(v, list):
            table.add_row(k, gen_list_output(v))
        else:
            # Handle long strings/URLs so they don't break the table
            value = str(v)

            if len(value) > 80:
                value = f"{value[:77]}..."

            table.add_row(k, hlt(value))

    return table


def gen_list_output(data_list: list):
    """Helper to decide how to show a list."""

    if not data_list:
        return hlt("[]")

    # If it's a list of dicts, stack them as nested tables
    if isinstance(data_list[0], dict):
        # We use a Grid or a transparent table to stack the nested dict tables
        stack = Table.grid(padding=(1, 0))
        for item in data_list:
            stack.add_row(gen_table(item))
        return stack

    # Otherwise, just return the highlighted string representation
    return hlt(str(data_list))
