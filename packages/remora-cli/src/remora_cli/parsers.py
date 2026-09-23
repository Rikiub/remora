import sys
from collections.abc import Generator, Iterable, Sequence
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any, Literal, Self, TextIO, get_args

from cyclopts import CycloptsError, Token, validators

from remora.models.search import SearchService

SearchTarget = Literal["url", SearchService]
_SERVICES: set[SearchTarget] = {entry for entry in get_args(SearchTarget)}


@dataclass(slots=True)
class Query:
    target: SearchTarget
    entry: str

    @classmethod
    def parse(cls, type_, tokens: Sequence[Token]) -> Generator[Self]:
        for token in tokens:
            if token.value == "-":
                yield from cls.from_lines(sys.stdin.read())
                break
            elif (path := Path(token.value)).is_file():
                validators.Path(
                    exists=True,
                    file_okay=True,
                    dir_okay=False,
                )(type_, path)
                yield from cls.from_file(path)
            else:
                yield cls.from_str(token.value)

    @classmethod
    def from_file(cls, path: Path) -> Generator[Self]:
        with path.open() as file:
            yield from cls.from_lines(file)

    @classmethod
    def from_lines(cls, content: str | TextIO) -> Generator[Self]:
        for line in StringIO(content) if isinstance(content, str) else content:
            if line.startswith(("http://", "https://")):
                yield cls(target="url", entry=line.strip())

    @classmethod
    def from_str(cls, query: str) -> Self:
        selection = query.split(":")[0]
        entry = query

        if query.startswith(("http://", "https://")):
            target = "url"
        elif selection in _SERVICES:
            target = selection  # type: ignore

            try:
                entry = query.split(":")[1].strip()
            except IndexError:
                raise CycloptsError(f"'{selection}' must have a entry.")
        else:
            raise CycloptsError(
                f"'{selection}' is invalid. Should be URL, service:query, or text FILE with list of URLs."
            )

        return cls(target=target, entry=entry)


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
