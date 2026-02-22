from typing import Annotated

from pydantic import AfterValidator

from remora._internal.path import validate_ffmpeg
from remora._internal.template.output import validate_template
from remora._internal.types.base import ExtensionType, ExtensionTypeLike
from remora._internal.types.extension import (
    StreamExtensionLike,
    StreamTargetLike,
    get_extension,
)
from remora.models._base import RemoraBaseModel
from remora.types import (
    DEFAULT_RETRIES,
    DEFAULT_TEMPLATE,
    StreamQuality,
    StrPath,
)


class DownloadOptions(RemoraBaseModel):
    """Configuration to shape the streams to download.

    If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

    Args:
        output_template: Directory where to save files.
        format: Target file format to search or convert if is a extension.
        quality: Target quality to try filter.
        ffmpeg_path: Path to FFmpeg executable. By default, it will get the global installed FFmpeg.
        embed_metadata: Embed title, uploader, thumbnail, subtitles, etc. (FFmpeg)
    """

    output_template: Annotated[
        StrPath,
        AfterValidator(validate_template),
    ] = DEFAULT_TEMPLATE
    format: StreamTargetLike = "video"
    quality: StreamQuality | int | None = None

    ffmpeg_path: Annotated[
        StrPath | None,
        AfterValidator(lambda v: validate_ffmpeg(v) if v else v),
    ] = None
    embed_metadata: bool = True

    max_workers: int = 4
    retries: int = DEFAULT_RETRIES

    @property
    def format_type(self) -> ExtensionTypeLike:
        """Determines category of the selected format.

        Returns:
            "video" or "audio".
        """

        try:
            target = ExtensionType(self.format)
            return target
        except ValueError:
            target = get_extension(self.format)
            return target.type

    @property
    def format_target(self) -> StreamExtensionLike | None:
        """Determines the specific extension: 'mp4', 'flac', etc.

        Returns:
            Extension if the format is a valid extension.
            None if the format is a generic type (e.g., 'video', 'audio').
        """

        try:
            extension = get_extension(self.format)
            if extension.is_safe:
                return extension
        except ValueError:
            return None
        return None
