from collections.abc import Generator, Iterable
from typing import Any, Literal, get_args

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
                f"'{selection}' is invalid. Should be URL or search SERVICE."
            )

        yield target, entry


def parse_keys(keys: Iterable[str]) -> set[str]:
    from remora._internal.template.key import validate_key
    from remora.exceptions import OutputTemplateError

    results = set()
    for key in keys:
        try:
            validate_key(key, True)
            results.add(key)
        except OutputTemplateError as e:
            raise CycloptsError(str(e))

    return results


def remove_missing(data: Any) -> Any:
    """Recursively removes None, [], and {} from a dictionary."""

    if isinstance(data, dict):
        return {
            k: v_clean
            for k, v in data.items()
            if (v_clean := remove_missing(v)) is not None
            and not (isinstance(v_clean, (list, dict, str)) and len(v_clean) == 0)
        }
    elif isinstance(data, list):
        return [v_clean for v in data if (v_clean := remove_missing(v)) is not None]
    return data
