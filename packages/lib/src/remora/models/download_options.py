from typing import Annotated

from pydantic import AfterValidator

from remora.constants import (
    DEFAULT_RETRIES,
    DEFAULT_TEMPLATE,
    DEFAULT_WORKERS,
)
from remora.ffmpeg import validate_ffmpeg_dir
from remora.models._base import RemoraModel
from remora.models.container import AVContainer, AVContainerFormat, RichAVContainer
from remora.models.stream import StreamQuality
from remora.models.types import StrPath
from remora.template import validate_template

__all__ = ["DownloadOptions"]


class DownloadOptions(RemoraModel):
    """Configuration to shape the streams to download.

    If FFmpeg is not installed, options marked as *[FFmpeg]* will not be available.

    Arguments:
        output_template: Path or template for the saved file(s).
        skip_existing: Skip downloading if a file with the same name already exists, regardless of extension.

        format_type: Target stream type to filter.
        quality: Target quality to filter.
            If `format_type` is not defined, then will filter only on videos by default.

        convert_to: Convert or remux the file by the given extension. *[FFmpeg]*
        embed_metadata: Embed title, uploader, thumbnail, subtitles, etc. *[FFmpeg]*
        ffmpeg_dir: Directory with both FFmpeg and FFprobe binaries. *[FFmpeg]*

        max_workers: Limit of simultaneous downloads.
    """

    output_template: Annotated[
        StrPath,
        AfterValidator(validate_template),
    ] = DEFAULT_TEMPLATE
    skip_existing: bool = True

    format_type: AVContainerFormat | None = None
    quality: StreamQuality | int | None = None

    convert_to: RichAVContainer | AVContainer | None = None
    embed_metadata: bool = True
    ffmpeg_location: Annotated[
        StrPath | None,
        AfterValidator(lambda v: validate_ffmpeg_dir(v) if v else v),
    ] = None

    max_workers: int = DEFAULT_WORKERS
    retries: int = DEFAULT_RETRIES
