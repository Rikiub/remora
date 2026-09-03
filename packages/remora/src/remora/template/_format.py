import re
import string
from pathlib import Path

from pathvalidate import sanitize_filepath
from typing_extensions import override

from remora.constants import DEFAULT_TEMPLATE
from remora.exceptions import OutputTemplateError
from remora.models._base import RemoraModel
from remora.models.media import Media, Playlist
from remora.models.stream import Stream
from remora.models.types import StrPath
from remora.template._generator import generate_keys

__all__ = ["format_template", "get_keys", "validate_key", "validate_template"]


class _Nested(RemoraModel):
    playlist: Playlist | None = None
    stream: Stream | None = None


# Generate one time and keep copy
_KEYS: set[str] = generate_keys([Media, _Nested])


class _TemplateFormatter(string.Formatter):
    def __init__(self, replace: str | None = None):
        self.replace = replace

    @override
    def get_field(self, field_name: str, args, kwargs):
        try:
            # Handle list.0 syntax as well
            field_name = re.sub(r"\.(\d+)", r"[\1]", field_name)

            # Python's built-in formatter natively resolve attributes/keys
            obj, used_key = super().get_field(field_name, args, kwargs)

            # Treat explicit None values as missing
            if obj is None:
                raise KeyError(field_name)

            return obj, used_key
        except (KeyError, AttributeError):
            # Fallback for missing keys or attributes
            final_value = (
                self.replace if self.replace is not None else f"{{{field_name}}}"
            )
            return final_value, field_name

    @override
    def format_field(self, value, format_spec):
        if value is None:
            return ""

        if format_spec == "upper":
            return str(value).upper()  # {title:upper} -> MY SONG
        elif format_spec == "lower":
            return str(value).lower()  # {title:lower} -> my song

        # Fallback to standard python behavior for everything else
        return super().format_field(value, format_spec)


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

    # Build metadata
    data = {}
    if media:
        for key in Media.model_fields:
            data[key] = getattr(media, key)
    if stream:
        data["stream"] = stream
    if playlist:
        data["playlist"] = playlist

    # Format with metadata
    formatter = _TemplateFormatter(replace=default_missing)
    output_template = formatter.format(str(output_template), **data)

    # Remove invalid characters and limit length
    path = sanitize_filepath(
        output_template,
        replacement_text="-",
    )
    return path


def validate_template(output: StrPath) -> StrPath:
    valid_keys = get_keys()

    for _, field_name, _, _ in string.Formatter().parse(str(output)):
        if not field_name or field_name.isdigit():
            continue

        # Strip brackets so "metadata[0]" or "metadata.0" becomes "metadata"
        base_key = re.sub(r"\[.*?\]|\.\d+", "", field_name)

        if base_key not in valid_keys:
            raise OutputTemplateError(f"Key '{{{field_name}}}' is invalid")

    return output


def validate_key(key: str) -> str:
    if key not in get_keys():
        raise OutputTemplateError(f"Key '{{{key}}}' is invalid")
    return key


def get_keys() -> set[str]:
    return _KEYS
