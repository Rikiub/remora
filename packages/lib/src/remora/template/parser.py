import re
import string
from pathlib import Path

from pathvalidate import sanitize_filepath
from remora.exceptions import OutputTemplateError
from remora.models.content.list import Playlist
from remora.models.content.media import Media
from remora.models.stream.types import Stream
from remora.template.keys import PlaylistNested
from remora.types import StrPath


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
    output: StrPath,
    stream: Stream | None = None,
    media: Media | None = None,
    playlist: Playlist | None = None,
    default_missing: str | None = None,
) -> Path:
    validate_template(output)

    data = {}

    if stream:
        data |= _flatten_dict(stream.model_dump())
    if media:
        data |= _flatten_dict(media.model_dump())
    if playlist:
        wrap_playlist = PlaylistNested(playlist=playlist)
        data |= _flatten_dict(wrap_playlist.model_dump())

    formatter = TemplateFormatter(replace=default_missing)
    template = formatter.format(str(output), **data)

    path = Path(sanitize_filepath(template, max_len=250))
    return path


def validate_template(output: StrPath):
    from remora.template.keys import get_keys

    pattern = r"{(.*?)}"
    keys: list[str] = re.findall(pattern, str(output))
    all_keys = get_keys()

    for key in keys:
        if key not in all_keys:
            raise OutputTemplateError(f"Key '{{{key}}}' from '{output}' is invalid.")


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
