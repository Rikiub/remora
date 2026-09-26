from typing import Annotated, Literal

from pydantic import AfterValidator

from remora.constants import (
    DEFAULT_TEMPLATE,
)
from remora.models._base import RemoraModel
from remora.models.container import AVContainer, AVContainerFormat, RichAVContainer
from remora.models.stream import StreamQuality
from remora.models.types import StrPath
from remora.template import validate_template

__all__ = ["DownloadOptions", "EmbedKind", "SidecarKind"]


def _validate_ffmpeg(value):
    if value:
        from remora.ffmpeg import validate_ffmpeg_dir

        return validate_ffmpeg_dir(value)
    return None


_Metadata = Literal["subtitles", "thumbnail", "info"]
EmbedKind = _Metadata
SidecarKind = _Metadata


class DownloadOptions(RemoraModel):
    """Configuration to shape the streams to download.

    If FFmpeg is not installed, options marked as *[FFmpeg]* will not be available.

    Arguments:
        output_template: Path or template for the saved file(s).
        skip_existing: Skip downloading if a file with the same name already exists, regardless of extension.
        concurrency: Limit of simultaneous downloads.
        retries: Limit of retries on errors.

        format_type: Target stream type to filter.
        quality: Target quality to filter.
            If `format_type` is not defined, then will filter only on videos by default.
        languages: Prefered audio and subtitle languages.

        streams: Include streams on download or not.
        embeds: Which artifacts to embed into the media file. *[FFmpeg]*
        sidecars: Which artifacts to write as separate files beside the media.

        convert_to: Convert or remux the file by the given extension. *[FFmpeg]*
        ffmpeg_dir: Directory with both FFmpeg and FFprobe binaries. *[FFmpeg]*
    """

    # Download
    output_template: Annotated[
        StrPath,
        AfterValidator(validate_template),
    ] = DEFAULT_TEMPLATE
    skip_existing: bool = True
    concurrency: int | None = None
    retries: int | None = None

    # Filter
    format_type: AVContainerFormat | None = None
    quality: StreamQuality | int | None = None
    languages: tuple[str, ...] | None = None

    # Metadata
    streams: bool = True
    embeds: tuple[EmbedKind, ...] | bool = True
    sidecars: tuple[SidecarKind, ...] | bool = False

    # Post-process
    convert_to: RichAVContainer | AVContainer | None = None
    ffmpeg_location: Annotated[StrPath | None, AfterValidator(_validate_ffmpeg)] = None

    def wants_metadata(self, value: EmbedKind) -> bool:
        return self.wants_embed(value) or self.wants_sidecar(value)

    def wants_embed(self, value: EmbedKind) -> bool:
        return self._wants(value, self.embeds)

    def wants_sidecar(self, value: SidecarKind) -> bool:
        return self._wants(value, self.sidecars)

    def _wants(
        self,
        value: str,
        target: tuple[str, ...] | bool,
    ) -> bool:
        if isinstance(target, bool):
            return target
        return value in (target or ())
