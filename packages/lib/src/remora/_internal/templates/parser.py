import string
from pathlib import Path

from pathvalidate import sanitize_filepath

from remora._internal.templates.keys import PlaylistNested
from remora.exceptions import OutputTemplateError
from remora.models.media.item import Media
from remora.models.media.list import Playlist
from remora.models.stream.item import Stream
from remora.types import DEFAULT_TEMPLATE, StrPath


class TemplateFormatter(string.Formatter):
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


def generate_output_template(
    template: StrPath,
    stream: Stream | None = None,
    media: Media | None = None,
    playlist: Playlist | None = None,
    default_missing: str | None = None,
) -> str:
    template_path = Path(template)

    # Set default if template is directory
    if str(template).endswith("/"):
        template = f"{template}{DEFAULT_TEMPLATE}"
    elif template_path.is_dir():
        template = template_path / DEFAULT_TEMPLATE

    validate_template(template)

    # Dump metadata
    data = {}
    if stream:
        data |= _flatten_dict(stream.model_dump())
    if media:
        data |= _flatten_dict(media.model_dump())
    if playlist:
        wrap_playlist = PlaylistNested(playlist=playlist)
        data |= _flatten_dict(wrap_playlist.model_dump())

    # Format with metadata
    formatter = TemplateFormatter(replace=default_missing)
    template = formatter.format(str(template), **data)

    # Remove invalid characters and limit length
    path = sanitize_filepath(template, max_len=250)
    return path


def validate_template(output: StrPath):
    import re

    from remora._internal.templates.keys import get_keys

    pattern = r"{(.*?)}"
    keys: list[str] = re.findall(pattern, str(output))
    all_keys = get_keys()

    for key in keys:
        if key not in all_keys:
            raise OutputTemplateError(f"Key '{{{key}}}' from '{output}' is invalid.")

    return output


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
