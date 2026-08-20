import string
from pathlib import Path

from pathvalidate import sanitize_filepath
from pydantic import BaseModel

from remora.constants import DEFAULT_TEMPLATE
from remora.exceptions import OutputTemplateError
from remora.models.media import Media, Playlist
from remora.models.stream import Stream
from remora.models.types import StrPath
from remora.template._generator import generate_keys


class _Nested(BaseModel):
    playlist: Playlist | None = None
    stream: Stream | None = None


# Generate one time and keep copy
_KEYS: set[str] = generate_keys([Media, _Nested])


class _TemplateFormatter(string.Formatter):
    def __init__(self, replace: str | None = None):
        self.replace = replace

    def get_field(self, field_name, args, kwargs):
        value = kwargs.get(field_name)

        if value is None:
            # If replace is provided, use it
            # Otherwise, return the original {key} string
            final_value = (
                self.replace if self.replace is not None else f"{{{field_name}}}"
            )
        else:
            final_value = value

        return final_value, field_name


def format_template(
    output_template: StrPath,
    stream: Stream | None = None,
    media: Media | None = None,
    playlist: Playlist | None = None,
    default_missing: str | None = None,
) -> str:
    template_path = Path(output_template)

    # Set default if template is directory
    if str(output_template).endswith("/"):
        output_template = f"{output_template}{DEFAULT_TEMPLATE}"
    elif template_path.is_dir():
        output_template = template_path / DEFAULT_TEMPLATE

    validate_template(output_template)

    # Dump metadata
    data = {}
    if stream:
        data |= _flatten_dict(stream.model_dump())
    if media:
        data |= _flatten_dict(media.model_dump())
    if playlist:
        wrap_playlist = _Nested(playlist=playlist)
        data |= _flatten_dict(wrap_playlist.model_dump())

    # Format with metadata
    formatter = _TemplateFormatter(replace=default_missing)
    output_template = formatter.format(str(output_template), **data)

    # Remove invalid characters and limit length
    path = sanitize_filepath(
        output_template,
        replacement_text="-",
    )
    return path


def validate_template(output: StrPath):
    import re

    pattern = r"{(.*?)}"
    keys: list[str] = re.findall(pattern, str(output))

    for key in keys:
        if key not in get_keys():
            raise OutputTemplateError(f"Key '{{{key}}}' is invalid")

    return output


def validate_key(key: str) -> str:
    if key not in get_keys():
        raise OutputTemplateError(f"Key '{{{key}}}' is invalid")
    return key


def get_keys() -> set[str]:
    return _KEYS


def _flatten_dict(d: dict, prefix: str = "") -> dict:
    items = {}

    for k, v in d.items():
        new_key = f"{prefix}{k}"
        if isinstance(v, dict):
            # Recursively flatten, but also keep the parent if it has data
            items.update(_flatten_dict(v, prefix=f"{new_key}."))
        else:
            items[new_key] = v

    return items
