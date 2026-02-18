from functools import partial, wraps
from typing import Any


def make_async(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        import anyio

        return anyio.run(partial(func, *args, **kwargs))

    return wrapper


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
