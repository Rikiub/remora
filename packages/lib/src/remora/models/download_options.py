from pathlib import Path
from typing import Annotated, cast, get_args

from pydantic import AfterValidator
from remora.models.base import RemoraBaseModel
from remora.types import (
    AUDIO_EXTENSION,
    EXTENSION,
    FILE_FORMAT,
    FORMAT_TYPE,
    VIDEO_EXTENSION,
    StrPath,
)

DEFAULT_OUTPUT_TEMPLATE = Path.cwd() / "{uploader.name} - {title}"


def _validate_template(template: StrPath):
    from remora.template.parser import validate_template

    validate_template(template)


def _validate_ffmpeg(value: StrPath | None):
    from remora.path import validate_ffmpeg

    if value:
        validate_ffmpeg(value)

    return value


class DownloadOptions(RemoraBaseModel):
    """Configuration to shape the streams to download.

    If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

    Args:
        format: Target file format to search or convert if is a extension.
        quality: Target quality to try filter.
        template: Directory where to save files.
        ffmpeg_path: Path to FFmpeg executable. By default, it will get the global installed FFmpeg.
        embed_metadata: Embed title, uploader, thumbnail, subtitles, etc. (FFmpeg)
    """

    format: FILE_FORMAT = "video"
    quality: int | None = None
    template: Annotated[
        StrPath,
        AfterValidator(_validate_template),
    ] = DEFAULT_OUTPUT_TEMPLATE
    ffmpeg_path: Annotated[
        StrPath | None,
        AfterValidator(_validate_ffmpeg),
    ] = None
    embed_metadata: bool = True
    max_workers: int = 4

    @property
    def type(self) -> FORMAT_TYPE:
        """Determine general type.

        Returns:
            "video" or "audio".
        """

        if self.format in get_args(FORMAT_TYPE):
            return cast(FORMAT_TYPE, self.format)

        elif self.format in get_args(VIDEO_EXTENSION):
            return "video"

        elif self.format in get_args(AUDIO_EXTENSION):
            return "audio"

        else:
            raise TypeError(self.format, "is invalid. Should be:", FILE_FORMAT)

    @property
    def convert(self) -> EXTENSION | None:
        """Check if would convert the files.

        Returns:
            If could convert, returns a file `EXTENSION`, else return `None`.
        """

        return (
            cast(EXTENSION, self.format) if self.format in get_args(EXTENSION) else None
        )
