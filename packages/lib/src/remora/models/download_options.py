from pathlib import Path
from typing import Annotated, cast, get_args

from pydantic import AfterValidator

from remora._internal.path import validate_ffmpeg
from remora._internal.templates.parser import validate_template
from remora.models._base import RemoraBaseModel
from remora.types import (
    DEFAULT_TEMPLATE,
    AudioExtension,
    StreamExtension,
    StreamQuality,
    StreamTarget,
    StreamType,
    StrPath,
    VideoExtension,
)


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

    format: StreamTarget = "video"
    quality: StreamQuality | int | None = None
    template: Annotated[
        StrPath,
        AfterValidator(validate_template),
    ] = Path.cwd() / DEFAULT_TEMPLATE
    ffmpeg_path: Annotated[
        StrPath | None,
        AfterValidator(lambda v: validate_ffmpeg(v) if v else v),
    ] = None
    embed_metadata: bool = True
    max_workers: int = 4

    @property
    def type(self) -> StreamType:
        """Determine general type.

        Returns:
            "video" or "audio".
        """

        if self.format in get_args(StreamType):
            return cast(StreamType, self.format)

        elif self.format in get_args(VideoExtension):
            return "video"

        elif self.format in get_args(AudioExtension):
            return "audio"

        else:
            raise ValueError(self.format, "is invalid. Should be:", StreamTarget)

    @property
    def convert(self) -> StreamExtension | None:
        """Check if would convert the files.

        Returns:
            If could convert, returns a file `EXTENSION`, else return `None`.
        """

        return (
            cast(StreamExtension, self.format)
            if self.format in get_args(StreamExtension)
            else None
        )
