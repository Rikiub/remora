from collections.abc import Sequence
from types import UnionType
from typing import Annotated, Union, get_args, get_origin

from pydantic import BaseModel, RootModel


def flatten_dict(d: dict, prefix: str = "") -> dict:
    items = {}

    for k, v in d.items():
        new_key = f"{prefix}{k}"
        if isinstance(v, dict):
            # Recursively flatten, but also keep the parent if it has data
            items.update(flatten_dict(v, prefix=f"{new_key}."))
        else:
            items[new_key] = v

    return items


def get_keys(models: Sequence[type[BaseModel]], flat: bool = False) -> set[str]:
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
    keys = set()
    if not hasattr(model, "model_fields"):
        return keys

    # Skip RootModel ".root" nesting visually
    if issubclass(model, RootModel):
        root_info = model.model_fields.get("root")
        if root_info:
            return _extract_recursive(
                _unwrap_type(root_info.annotation),
                prefix=prefix,
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
            )

        if not flat and child_keys:
            keys.update(child_keys)
        else:
            keys.add(full_key)

    return keys


def _unwrap_type(t):
    if t is None:
        return None

    origin = get_origin(t)
    args = get_args(t)

    if origin is Annotated:
        return _unwrap_type(args[0])
    if origin in (Union, UnionType):
        valid_args = [a for a in args if a is not type(None)]
        return _unwrap_type(valid_args[0]) if valid_args else None
    if origin in (list, dict):
        return _unwrap_type(args[-1]) if args else None
    return t
