from typing import AsyncIterable
from loguru import logger
from remora.exceptions import MediaError
from remora.extractor import MediaExtractor
from remora.models.content.list import Search
from remora.models.content.types import ExtractResult
from remora_cli.completions import parse_queries
from remora_cli.ui.rich import Status
from rich.highlighter import ReprHighlighter
from rich.table import Table
from typer import Exit


async def extract_queries(
    queries: list[str],
    extractor: MediaExtractor,
) -> AsyncIterable[ExtractResult | Search]:
    for target, entry in parse_queries(queries):
        try:
            with Status("Searching[blink]...[/]"):
                if target == "url":
                    logger.info('🔎 Extract URL: "{url}"', url=entry)
                    result = await extractor.extract_url(entry)

                    if result.type == "playlist":
                        logger.info('🔎 Playlist title: "{title}"', title=result.title)

                        if not result.medias and result.playlists:
                            logger.warning(
                                "❗ The URL only have multiple playlists but no medias, please try again with a single playlist."
                            )
                            raise Exit()
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


def get_table(data: dict) -> Table:
    data = flatten_data(data)

    high = ReprHighlighter()
    table = Table(show_header=False, box=None)

    for key, value in data.items():
        table.add_row(f"[yellow]{key}[/]", high(str(value)))

    return table


def flatten_data(data, parent_key="", sep="."):
    items = []

    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            items.extend(flatten_data(value, new_key, sep=sep).items())

    elif isinstance(data, list):
        if data and isinstance(data[0], dict):
            for index, value in enumerate(data):
                new_key = f"{parent_key}{sep}{index}" if parent_key else str(index)
                items.extend(flatten_data(value, new_key, sep=sep).items())
        else:
            items.append((parent_key, data))

    else:
        items.append((parent_key, data))

    return dict(items)
