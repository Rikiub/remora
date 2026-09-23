from collections.abc import AsyncIterable, Iterable

from loguru import logger
from pydantic import AnyUrl
from rich import box
from rich.highlighter import ReprHighlighter
from rich.table import Table

from remora import Remora
from remora.exceptions import RemoraError
from remora.models.media import ExtractResult, Search
from remora_cli.parsers import Query, SearchTarget
from remora_cli.ui.rich import CONSOLE


async def extract_queries(
    queries: Iterable[Query],
    remora: Remora,
) -> AsyncIterable[tuple[SearchTarget, ExtractResult | Search]]:
    for query in queries:
        try:
            if (
                query.target == "url"
                and (cookies := remora._session.network_options.cookies)
                and (url_host := AnyUrl(query.entry).host)
                and cookies.get_expired_cookies(url_host)
            ):
                logger.warning(
                    f"The given cookies for the domain '{url_host}' are expired. "
                    "It could do unexpected behaviour. "
                    "Please update your cookies file the next time."
                )

            with CONSOLE.status("Searching[blink]...[/]"):
                if query.target == "url":
                    logger.info('Extract URL: "{url}"', url=query.entry, icon="🔎")
                    result = await remora.extract(query.entry)

                    if result.type == "playlist":
                        logger.info(
                            'Playlist title: "{title}"',
                            title=result.title,
                            icon="🔎",
                        )

                else:
                    logger.info(
                        'Search from {extractor}: "{query}"',
                        extractor=query.target,
                        query=query.entry,
                        icon="🔎",
                    )

                    result = await remora.extract_search(query.entry, query.target)

                    if not result.entries.medias():
                        logger.warning("No results found")
                        raise SystemExit()

                await logger.complete()
            yield query.target, result
        except RemoraError as error:
            logger.error("{message}", message=str(error))


_hlt = ReprHighlighter()


def dict_to_table(data: dict) -> Table:
    table = Table(title=None, show_header=False, box=box.ROUNDED)
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value")

    for key, value in data.items():
        if isinstance(value, dict):
            table.add_row(key, _gen_table(value))
        elif isinstance(value, list):
            table.add_row(key, _gen_list_output(value))
        else:
            table.add_row(key, _hlt(str(value)))

    return table


def _gen_table(data: dict) -> Table:
    table = Table(show_header=False, box=box.ROUNDED, padding=(0, 1))
    table.add_column("K", style="bold yellow", no_wrap=True)
    table.add_column("V")

    for k, v in data.items():
        if isinstance(v, dict):
            table.add_row(k, _gen_table(v))
        elif isinstance(v, list):
            table.add_row(k, _gen_list_output(v))
        else:
            # Handle long strings/URLs so they don't break the table
            value = str(v)

            if len(value) > 80:
                value = f"{value[:77]}..."

            table.add_row(k, _hlt(value))

    return table


def _gen_list_output(data_list: list):
    """Helper to decide how to show a list."""

    if not data_list:
        return _hlt("[]")

    # If it's a list of dicts, stack them as nested tables
    if isinstance(data_list[0], dict):
        # We use a Grid or a transparent table to stack the nested dict tables
        stack = Table.grid(padding=(1, 0))
        for item in data_list:
            stack.add_row(_gen_table(item))
        return stack

    # Otherwise, just return the highlighted string representation
    return _hlt(str(data_list))
