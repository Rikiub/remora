from pathlib import Path
from typing import Annotated, cast, get_args

from pydantic import AfterValidator, field_validator
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


def _validate_output(template: StrPath):
    from remora.template.parser import validate_output

    validate_output(template)


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
        AfterValidator(_validate_output),
    ] = DEFAULT_OUTPUT_TEMPLATE
    ffmpeg_path: StrPath | None = None
    embed_metadata: bool = True
    max_workers: int = 4

    @field_validator("ffmpeg_path")
    @classmethod
    async def _validate_ffmpeg(self):
        from remora.path import validate_ffmpeg

        if self.ffmpeg_path:
            await validate_ffmpeg(self.ffmpeg_path)

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
