from anyio import Path
from typing_extensions import override

from remora.downloader.format.base import DEFAULT_RETRIES, BaseFormatDownloader
from remora.downloader.format.httpx import HttpxFormatDownloader
from remora.exceptions import DownloadError
from remora.models.format.types import Format
from remora.models.progress.format import FormatDownloadCallback
from remora.types import StrPath


class FormatDownloader(BaseFormatDownloader):
    def __init__(
        self,
        filepath: StrPath,
        format: Format,
        on_progress: FormatDownloadCallback | None = None,
        duration: float | None = None,
        retries: int = DEFAULT_RETRIES,
    ):
        super().__init__(filepath, format, on_progress, retries)
        self.duration = duration

    @override
    async def download(self) -> Path:
        try:
            return await HttpxFormatDownloader(
                self.filepath,
                self.format,
                self.progress,
                self.retries,
                duration=self.duration,
            ).download()
        except (TypeError, DownloadError) as e:
            if (
                isinstance(e, TypeError)
                or isinstance(e, DownloadError)
                and e.status_code == 403
            ):
                from remora.downloader.format.ydl import YDLFormatDownloader

                return await YDLFormatDownloader(
                    self.filepath,
                    self.format,
                    self.progress,
                    self.retries,
                ).download()

            raise
