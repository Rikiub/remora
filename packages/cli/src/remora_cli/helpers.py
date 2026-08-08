from typing import Any


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
