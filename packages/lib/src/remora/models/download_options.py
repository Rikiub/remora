from typing import Annotated

from pydantic import AfterValidator

from remora._internal.ffmpeg import validate_ffmpeg
from remora._internal.template.output import validate_template
from remora.models._base import RemoraModel
from remora.models.container import ContainerFormat, ExtensionLike
from remora.types import (
    DEFAULT_RETRIES,
    DEFAULT_TEMPLATE,
    DEFAULT_WORKERS,
    StreamQuality,
    StrPath,
)


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
        ffmpeg_path: Path to custom FFmpeg executable. *[FFmpeg]*

        max_workers: Limit of simultaneous downloads.
    """

    output_template: Annotated[
        StrPath,
        AfterValidator(validate_template),
    ] = DEFAULT_TEMPLATE
    skip_existing: bool = True

    format_type: ContainerFormat | None = None
    quality: StreamQuality | int | None = None

    convert_to: ExtensionLike | None = None
    embed_metadata: bool = True
    ffmpeg_path: Annotated[
        StrPath | None,
        AfterValidator(lambda v: validate_ffmpeg(v) if v else v),
    ] = None

    max_workers: int = DEFAULT_WORKERS
    retries: int = DEFAULT_RETRIES


__all__ = ["DownloadOptions"]
