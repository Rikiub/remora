import functools
import operator
from collections.abc import Sequence
from types import UnionType
from typing import Annotated, Any, TypeVar, Union, get_args, get_origin

import typing_extensions
from pydantic import BaseModel, RootModel

__all__ = ["generate_keys"]

_NO_DEFAULT = getattr(typing_extensions, "NoDefault", object())


def generate_keys(models: Sequence[type[BaseModel]], flat: bool = False) -> set[str]:
    """Generate keys from model fields."""

    keys = set()

    for model in models:
        keys.update(_extract_recursive(model, flat=flat))

    return keys


def _extract_recursive(
    model: Any,
    prefix: str = "",
    flat: bool = False,
    ancestors: frozenset[Any] = frozenset(),
) -> set[str]:
    keys: set[str] = set()
    if model is None or model in ancestors:
        return keys

    origin = get_origin(model)
    if origin in (Union, UnionType):
        for arg in get_args(model):
            if arg is not type(None):
                keys.update(
                    _extract_recursive(
                        arg,
                        prefix=prefix,
                        flat=flat,
                        ancestors=ancestors,
                    )
                )
        return keys

    if not hasattr(model, "model_fields"):
        return keys

    # Skip RootModel ".root" nesting visually
    if isinstance(model, type) and issubclass(model, RootModel):
        root_info = model.model_fields.get("root")
        if root_info:
            return _extract_recursive(
                _unwrap_type(root_info.annotation),
                prefix=prefix,
                flat=flat,
                ancestors=ancestors | {model},
            )

    current_ancestors = ancestors | {model}
    for name, info in model.model_fields.items():
        full_key = f"{prefix}{name}"
        target_type = _unwrap_type(info.annotation)

        # Try to get children first
        child_keys = set()
        if target_type:
            child_keys = _extract_recursive(
                target_type,
                prefix=f"{full_key}.",
                flat=flat,
                ancestors=current_ancestors,
            )

        # Add child paths
        if not flat and child_keys:
            keys.update(child_keys)
        # Add base key
        else:
            keys.add(full_key)

    return keys


def _is_sequence_type(t: Any) -> bool:
    """Check if a type annotation represents a list, set, tuple, or Sequence."""
    if t is None:
        return False

    origin = get_origin(t)

    if origin is Annotated:
        return _is_sequence_type(get_args(t)[0])

    if origin in (Union, UnionType):
        valid_args = [a for a in get_args(t) if a is not type(None)]
        return any(_is_sequence_type(a) for a in valid_args)

    target = origin if origin is not None else t
    if isinstance(target, type):
        if issubclass(target, RootModel):
            return False
        return issubclass(target, (list, set, tuple, Sequence)) and target not in (
            str,
            bytes,
        )

    return False


def _unwrap_type(t: Any) -> Any:
    if t is None:
        return None

    if isinstance(t, TypeVar):
        default = getattr(t, "__default__", None)
        if default is not None and default is not _NO_DEFAULT:
            return _unwrap_type(default)
        bound = getattr(t, "__bound__", None)
        if bound is not None:
            return _unwrap_type(bound)
        return None

    origin = get_origin(t)
    args = get_args(t)

    if origin is Annotated:
        return _unwrap_type(args[0])

    if origin in (Union, UnionType):
        valid_args = [a for a in args if a is not type(None)]
        if not valid_args:
            return None
        if len(valid_args) == 1:
            return _unwrap_type(valid_args[0])

        unwrapped = [_unwrap_type(a) for a in valid_args]
        unwrapped = [u for u in unwrapped if u is not None]

        if not unwrapped:
            return None
        if len(unwrapped) == 1:
            return unwrapped[0]
        try:
            return functools.reduce(operator.or_, unwrapped)
        except TypeError:
            return Union[tuple(unwrapped)]  # noqa: UP007

    if isinstance(t, type) and issubclass(t, RootModel):
        root_info = t.model_fields.get("root")
        if root_info:
            return _unwrap_type(root_info.annotation)

    if origin in (dict,):
        return _unwrap_type(args[-1]) if args else None

    if _is_sequence_type(t):
        return _unwrap_type(args[0]) if args else None

    return t
