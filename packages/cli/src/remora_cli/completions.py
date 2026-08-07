from collections.abc import Generator
from typing import Literal, get_args

from cyclopts import CycloptsError

from remora.models.search import SearchService

SearchTarget = Literal["url", SearchService]


def parse_queries(
    queries: list[str],
) -> Generator[tuple[SearchTarget, str], None, None]:
    providers: list[SearchTarget] = [entry for entry in get_args(SearchTarget)]
    target: SearchTarget

    for entry in queries:
        selection = entry.split(":")[0]

        if entry.startswith(("http://", "https://")):
            target = "url"
        elif selection in providers:
            target = selection  # type: ignore
            entry = entry.split(":")[1].strip()
        else:
            raise CycloptsError(
                f"'{selection}' is invalid. Should be URL or search PROVIDER."
            )

        yield target, entry
