from typing import AsyncIterable
from remora.downloader.config import DEFAULT_OUTPUT_TEMPLATE, FormatConfig
from remora.downloader.type.batch import DownloadBatch
from remora.downloader.type.pipeline import DownloadPipeline
from remora.extractor import MediaExtractor
from remora.models.content.media import LazyMedia
from remora.models.content.types import AnyExtractResult
from remora.models.event.main import DownloadEvent
from remora.models.event.media import MediaEvent
from remora.types import FILE_FORMAT, StrPath


class MediaDownloader:
    def __init__(
        self,
        format: FILE_FORMAT = "video",
        quality: int | None = None,
        output: StrPath = DEFAULT_OUTPUT_TEMPLATE,
        max_workers: int = 4,
        ffmpeg_path: StrPath | None = None,
        embed_metadata: bool = True,
        extractor: MediaExtractor | None = None,
    ):
        """Multi-thread media downloader.

        If FFmpeg is not installed, options marked with (FFmpeg) will not be available.

        Args:
            format: File format to search or convert with (FFmpeg) if is a extension.
            quality: Quality to filter.
            output: Directory where to save files.
            threads: Maximum processes to execute.
            ffmpeg_path: Path to FFmpeg executable. By default, it will get the global installed FFmpeg.
            embed_metadata: Embed title, uploader, thumbnail, subtitles, etc. (FFmpeg)

        Raises:
            FileNotFoundError: `ffmpeg` path not is a FFmpeg executable.
        """

        self.config = FormatConfig(
            format=format,
            quality=quality,
            output=output,
            ffmpeg_path=ffmpeg_path,
            embed_metadata=embed_metadata,
        )
        self.extractor = extractor

    async def download(self, media: LazyMedia) -> AsyncIterable[MediaEvent]:
        """Single download a `Media` result.

        Args:
            media: Target `Media` to download.

        Returns:
            Path to downloaded file.
        """

        async for event in DownloadPipeline(
            media,
            format_config=self.config,
            extractor=self.extractor,
        ).run():
            yield event

    async def download_batch(
        self, data: AnyExtractResult
    ) -> AsyncIterable[DownloadEvent]:
        """Batch download any result.

        Returns:
            List of paths to downloaded files.
        """

        async for event in DownloadBatch(
            data,
            format_config=self.config,
            extractor=self.extractor,
        ).run():
            yield event
