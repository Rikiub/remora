from typing import Annotated

from pydantic import AfterValidator

from remora._internal.ffmpeg import validate_ffmpeg
from remora._internal.template.output import validate_template
from remora.models._base import RemoraModel
from remora.models.container.extension.types import ExtensionType
from remora.models.container.format import FormatType
from remora.types import DEFAULT_RETRIES, DEFAULT_TEMPLATE, StreamQuality, StrPath


class DownloadOptions(RemoraModel):
    """Configuration to shape the streams to download.

    If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

    Arguments:
        output_template: Directory where to save files.
        format_type: Streams format to filter.
        convert_to: Convert or remux the file by the given extension.
        quality: Target quality to try filter.
        ffmpeg_path: Path to FFmpeg executable.
        embed_metadata: Embed title, uploader, thumbnail, subtitles, etc. (FFmpeg)
    """

    output_template: Annotated[
        StrPath,
        AfterValidator(validate_template),
    ] = DEFAULT_TEMPLATE

    format_type: FormatType = "video"
    convert_to: ExtensionType | None = None
    quality: StreamQuality | int | None = None

    ffmpeg_path: Annotated[
        StrPath | None,
        AfterValidator(lambda v: validate_ffmpeg(v) if v else v),
    ] = None
    embed_metadata: bool = True

    max_workers: int = 4
    retries: int = DEFAULT_RETRIES
