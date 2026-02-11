from anyio import Path

from remora.downloader.config import DEFAULT_OUTPUT_TEMPLATE, FormatConfig
from remora.downloader.type.bulk import DownloadBulk
from remora.extractor import MediaExtractor
from remora.models.content.list import MediaList
from remora.models.content.media import LazyMedia
from remora.models.content.types import ExtractResult, MediaListEntries
from remora.models.progress.list import PlaylistDownloadCallback
from remora.models.progress.media import MediaDownloadCallback
from remora.types import FILE_FORMAT, StrPath

_MediaResult = ExtractResult | MediaListEntries
MediaResult = MediaList | _MediaResult | list[LazyMedia]


class MediaDownloader:
    def __init__(
        self,
        format: FILE_FORMAT = "video",
        quality: int | None = None,
        output: StrPath = DEFAULT_OUTPUT_TEMPLATE,
        threads: int = 4,
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
        self.threads = threads

    async def download(
        self,
        media: LazyMedia,
        on_progress: MediaDownloadCallback | None = None,
    ) -> Path:
        """Single download a `Media` result.

        Args:
            media: Target `Media` to download.
            on_progress: Callback function to get progress information.

        Returns:
            Path to downloaded file.
        """

        paths = await DownloadBulk(
            media,
            format_config=self.config,
            extractor=self.extractor,
            on_progress=on_progress,
        ).run()
        return paths[0]

    async def download_all(
        self,
        data: MediaResult,
        on_progress: MediaDownloadCallback | None = None,
        on_playlist: PlaylistDownloadCallback | None = None,
    ) -> list[Path]:
        """Batch download any result.

        Returns:
            List of paths to downloaded files.
        """

        return await DownloadBulk(
            data,
            self.config,
            self.extractor,
            self.threads,
            on_progress,
            on_playlist,
        ).run()
