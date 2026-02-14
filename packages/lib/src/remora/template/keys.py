"""Read pre-serialized keys from JSON to improve startup time on shell autocomplete."""

from pydantic import RootModel, BaseModel
from remora.models.content.media import Media
from remora.models.content.list import Playlist
from types import UnionType
from typing import Annotated, Union, get_args, get_origin


class PlaylistNested(BaseModel):
    playlist: Playlist


MODELS = {Media, PlaylistNested}
EXCLUDED_KEYS = {
    "extractor_key",
    "type",
    "_type",
    "extension",
    "heatmap",
    "is_cache",
    "medias",
    "entries",
    "playlists",
    "chapters",
    "subtitles",
    "thumbnails",
    "playlist.extractor",
    "playlist.uploader",
    "playlist.type",
    "playlist.entries",
    "playlist.thumbnails",
    "streams.cookies",
    "streams.http_headers",
    "streams.downloader_options",
}


def get_keys() -> list[str]:
    import json
    from pathlib import Path

    keys: list[str]

    filepath = Path(__file__)
    filepath = filepath.parent / f"{filepath.stem}.json"

    if filepath.is_file():
        with filepath.open() as f:
            keys = json.load(f)
    else:
        keys = list(_generate_keys())
        filepath.write_text(json.dumps(keys))

    return keys


def _generate_keys() -> list[str]:
    """Should be executed only one time."""

    def unwrap_type(t):
        if t is None:
            return None
        origin = get_origin(t)
        args = get_args(t)

        if origin is Annotated:
            return unwrap_type(args[0])
        if origin in (Union, UnionType):
            valid_args = [a for a in args if a is not type(None)]
            return unwrap_type(valid_args[0]) if valid_args else None
        if origin in (list, dict):
            return unwrap_type(args[-1]) if args else None
        return t

    def extract_recursive(
        model: type,
        prefix: str = "",
        use_alias: bool = False,
    ) -> list[str]:
        keys = []
        if not hasattr(model, "model_fields"):
            return keys

        # Skip RootModel ".root" nesting visually
        if issubclass(model, RootModel):
            root_info = model.model_fields.get("root")
            if root_info:
                return extract_recursive(
                    unwrap_type(root_info.annotation),  # type: ignore
                    prefix=prefix,
                    use_alias=use_alias,
                )

        for name, info in model.model_fields.items():
            token = info.alias if use_alias and info.alias else name
            full_key = f"{prefix}{token}"

            target_type = unwrap_type(info.annotation)

            # 1. Try to get children first
            child_keys = []
            if target_type and hasattr(target_type, "model_fields"):
                child_keys = extract_recursive(
                    target_type, prefix=f"{full_key}.", use_alias=use_alias
                )

            # 2. DECISION: If it has children, only add the children.
            # If it has NO children, it's a leaf, so add the full_key.
            if child_keys:
                keys.extend(child_keys)
            else:
                keys.append(full_key)

        return keys

    # Generate the templates using the recursive function
    templates = set()

    for model in MODELS:
        templates.update(extract_recursive(model))

    # Clean up excluded keys
    filtered_keys = {
        k
        for k in templates
        if not any(k == key or k.startswith(f"{key}.") for key in EXCLUDED_KEYS)
    }

    return sorted(list(filtered_keys))
