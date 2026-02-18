import string
from pathlib import Path

from pathvalidate import sanitize_filepath

from remora._internal.template.generator import flatten_dict
from remora._internal.template.key import PlaylistNested
from remora._internal.template.key import get_keys as _get_keys
from remora.exceptions import OutputTemplateError
from remora.models.media.item import Media
from remora.models.media.list import Playlist
from remora.models.stream.item import Stream
from remora.types import DEFAULT_TEMPLATE, StrPath

_OUTPUT_EXCLUDED_KEYS = {
    "extension",
    "heatmap",
    "chapters",
    "subtitles",
    "thumbnails",
    "streams",
    "is_cache",
    "playlist.is_cache",
    "playlist.entries",
    "playlist.thumbnails",
}
_KEYS = {
    k
    for k in _get_keys()
    if not any(k == key or k.startswith(f"{key}.") for key in _OUTPUT_EXCLUDED_KEYS)
}


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
        data |= flatten_dict(stream.model_dump())
    if media:
        data |= flatten_dict(media.model_dump())
    if playlist:
        wrap_playlist = PlaylistNested(playlist=playlist)
        data |= flatten_dict(wrap_playlist.model_dump())

    # Format with metadata
    formatter = _TemplateFormatter(replace=default_missing)
    output_template = formatter.format(str(output_template), **data)

    # Remove invalid characters and limit length
    path = sanitize_filepath(output_template, max_len=250)
    return path


def validate_template(output: StrPath):
    import re

    pattern = r"{(.*?)}"
    keys: list[str] = re.findall(pattern, str(output))

    for key in keys:
        if key not in get_keys():
            raise OutputTemplateError(f"Key '{{{key}}}' is invalid")

    return output


def validate_key(key: str):
    if key not in get_keys():
        raise OutputTemplateError(f"Key '{{{key}}}' is invalid")
    return key


def get_keys() -> set[str]:
    return _KEYS
