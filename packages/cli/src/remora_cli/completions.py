from typing import Generator, Literal, get_args

from remora.types import SearchService, StreamQuality
from typer import BadParameter

SearchTarget = Literal["url", SearchService]


def complete_query(incomplete: str) -> Generator[str, None, None]:
    for name in get_args(SearchTarget):
        if name.startswith(incomplete):
            yield name + ":"


def complete_resolution() -> Generator[str, None, None]:
    for name in get_args(StreamQuality):
        yield str(name)


def complete_template_key() -> Generator[str, None, None]:
    from remora.template.keys import get_keys

    for key in get_keys():
        yield key


def complete_output(incomplete: str) -> Generator[str, None, None]:
    if incomplete.endswith("{"):
        for key in complete_template_key():
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
