from collections.abc import Sequence
from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin

from pydantic import BaseModel, RootModel

__all__ = ["generate_keys"]


def generate_keys(models: Sequence[type[BaseModel]], flat: bool = False) -> set[str]:
    """Generate keys from model fields."""

    keys = set()

    for model in models:
        keys.update(_extract_recursive(model, flat=flat))

    return keys


def _extract_recursive(
    model: type[BaseModel],
    prefix: str = "",
    flat: bool = False,
) -> set[str]:
    keys: set[str] = set()
    if not hasattr(model, "model_fields"):
        return keys

    # Skip RootModel ".root" nesting visually
    if issubclass(model, RootModel):
        root_info = model.model_fields.get("root")
        if root_info:
            return _extract_recursive(
                _unwrap_type(root_info.annotation),
                prefix=prefix,
                flat=flat,
            )

    for name, info in model.model_fields.items():
        full_key = f"{prefix}{name}"
        target_type = _unwrap_type(info.annotation)

        # Try to get children first
        child_keys = {}
        if target_type and hasattr(target_type, "model_fields"):
            child_keys = _extract_recursive(
                target_type,
                prefix=f"{full_key}.",
                flat=flat,
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
        return issubclass(target, (list, set, tuple, Sequence)) and target not in (
            str,
            bytes,
        )

    return False


def _unwrap_type(t: Any) -> Any:
    if t is None:
        return None

    origin = get_origin(t)
    args = get_args(t)

    if origin is Annotated:
        return _unwrap_type(args[0])
    if origin in (Union, UnionType):
        valid_args = [a for a in args if a is not type(None)]
        return _unwrap_type(valid_args[0]) if valid_args else None
    if origin in (dict,):
        return _unwrap_type(args[-1]) if args else None

    # Unwrap RootModels
    target = origin if origin is not None else t
    if isinstance(target, type) and issubclass(target, RootModel):
        # Handle inline generic: RootModel[list[Stream]]
        if origin is not None and args:
            return _unwrap_type(args[0])
        # Handle subclass: class StreamList(RootModel[list[Stream]])
        if hasattr(target, "model_fields"):
            root_info = target.model_fields.get("root")
            if root_info:
                return _unwrap_type(root_info.annotation)

    if _is_sequence_type(t):
        return _unwrap_type(args[0]) if args else None

    return t
