from collections.abc import AsyncIterable

from loguru import logger
from rich import box
from rich.highlighter import ReprHighlighter
from rich.table import Table
from typer import Exit

from remora import MediaExtractor
from remora.exceptions import MediaError
from remora.models.content.list import SearchList
from remora.models.content.types import ExtractResult
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
        except MediaError as error:
            logger.error("❌ {error}", error=str(error))
        finally:
            logger.info("")


hlt = ReprHighlighter()


def dict_to_table(data: dict, title: str = "Model Details") -> Table:
    table = Table(show_header=False, box=box.ROUNDED)
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value")

    for key, value in data.items():
        # If the value is a nested dict/model, recurse
        if isinstance(value, dict):
            table.add_row(key, gen_table(value, title=key))
        elif isinstance(value, list):
            # For lists, we can create a bulleted-style table or join them
            table.add_row(key, hlt(str(value)))
        else:
            table.add_row(key, hlt(str(value)))

    return table


def gen_table(data: dict, title: str) -> Table:
    table = Table(show_header=False, box=box.ROUNDED, padding=(0, 2))
    table.add_column("K", style="bold yellow")
    table.add_column("V")

    for k, v in data.items():
        if isinstance(v, dict):
            table.add_row(k, gen_table(v, title=k))
        else:
            table.add_row(k, hlt(str(v)))

    return table
