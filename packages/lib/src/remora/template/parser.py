import re
from pathlib import Path
from typing import Literal

from pathvalidate import sanitize_filepath
from remora.exceptions import OutputTemplateError
from remora.models.content.list import Playlist
from remora.models.content.media import Media
from remora.models.stream.types import Stream
from remora.template.keys import get_keys
from remora.types import StrPath


class FormatterDict(dict):
    def __init__(self, *args, replace: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.replace = replace

    def __missing__(self, key):
        if self.replace:
            return self.replace
        else:
            return f"{{{key}}}"


def generate_output_template(
    output: StrPath,
    media: Media | None = None,
    playlist: Playlist | None = None,
    stream: Stream | None = None,
    default_missing: str | None = None,
) -> Path:
    validate_output(output)

    data = {}

    if stream:
        data |= stream.model_dump(exclude_none=True)
        data |= stream.model_dump(by_alias=True, exclude_none=True)
    if playlist:
        data |= playlist.model_dump(by_alias=True, exclude_none=True)
    if media:
        data |= media.model_dump(exclude_none=True)

    safe_data = FormatterDict(data, replace=default_missing)
    template = str(output).format_map(safe_data)

    path = Path(sanitize_filepath(template, max_len=250))
    return path


def validate_output(output: StrPath) -> Literal[True]:
    pattern = r"{(.*?)}"
    keys: list[str] = re.findall(pattern, str(output))

    for key in keys:
        if key not in get_keys():
            raise OutputTemplateError(f"Key '{{{key}}}' from '{output}' is invalid.")

    return True
