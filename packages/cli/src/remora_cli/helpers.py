import types
from typing import Any, Literal, Union, get_args, get_origin


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


def unwrap_literals(literals: Any) -> tuple[Any, ...]:
    origin = get_origin(literals)

    if origin is Literal:
        return get_args(literals)

    if origin is Union or origin is types.UnionType:
        values = []

        for arg in get_args(literals):
            values.extend(unwrap_literals(arg))

        return tuple(values)

    return ()
