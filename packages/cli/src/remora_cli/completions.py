from collections.abc import Generator
from typing import Literal, get_args

from typer import BadParameter

from remora.models.search import SearchServiceStr
from remora.types import StreamQuality

SearchTarget = Literal["url", SearchServiceStr]


def complete_query(incomplete: str) -> Generator[str, None, None]:
    for name in get_args(SearchTarget):
        if name.startswith(incomplete):
            yield name + ":"


def complete_resolution() -> Generator[str, None, None]:
    for name in get_args(StreamQuality):
        yield str(name)


def complete_template_key() -> Generator[str, None, None]:
    from remora._internal.template.key import get_keys

    yield from get_keys(True)


def complete_output(incomplete: str) -> Generator[str, None, None]:
    if incomplete.endswith("{"):
        from remora._internal.template.output import get_keys

        for key in get_keys():
            yield incomplete + key + "}"


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
            completed = [i for i in complete_query(selection)]

            if completed:
                msg = f"Did you mean '{completed[0]}'?"
            else:
                msg = "Should be URL or search PROVIDER."

            raise BadParameter(f"'{selection}' is invalid. {msg}")

        yield target, entry
