from collections.abc import Generator, Iterable
from typing import Any, Literal, get_args

from cyclopts import CycloptsError

from remora.models.search import SearchService

SearchTarget = Literal["url", SearchService]


def parse_queries(queries: Iterable[str]) -> Generator[tuple[SearchTarget, str]]:
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
    from remora.exceptions import OutputTemplateError
    from remora.template import validate_key

    results = set()
    for key in keys:
        try:
            key = validate_key(key)
            results.add(key)
        except OutputTemplateError as e:
            raise CycloptsError(str(e))

    return results


# Remove missing helper
_EMPTY = (list, tuple, dict, set, frozenset)


def _is_empty_container(x):
    return isinstance(x, _EMPTY) and len(x) == 0


def remove_missing(data: Any, *, drop_empty: bool = True) -> Any:
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            c = remove_missing(v, drop_empty=drop_empty)
            if c is None:
                continue
            if drop_empty and _is_empty_container(c):
                continue
            out[k] = c
        return out

    if isinstance(data, (list, tuple)):
        c = [remove_missing(v, drop_empty=drop_empty) for v in data]
        c = [v for v in c if v is not None]  # only None here
        return type(data)(c) if not isinstance(data, tuple) else tuple(c)

    if isinstance(data, (set, frozenset)):
        c = {remove_missing(v, drop_empty=drop_empty) for v in data}
        return type(data)(v for v in c if v is not None)

    return data
