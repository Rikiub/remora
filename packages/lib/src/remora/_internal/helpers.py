from functools import cache
from typing import Any, get_args


@cache
def literal_to_set(tp: Any) -> frozenset[str]:
    """Flattens nested Literals/Unions into a single set of strings."""

    # Get children
    args = get_args(tp)

    # Open each children. If it's Literal, get its content.
    # If it's just a string, keep it.
    return frozenset(
        value for arg in args for value in (get_args(arg) if get_args(arg) else (arg,))
    )
