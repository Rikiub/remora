from pathlib import Path

from remora.downloader.format.httpx import HttpxFormatDownloader
from remora.downloader.format.ydl import YDLFormatDownloader
from remora.exceptions import DownloadError
from remora.models.format.types import Format
from remora.models.progress.format import FormatDownloadCallback


class FormatDownloader:
    def __init__(
        self,
        filepath: Path,
        format: Format,
        duration: float | None = None,
        on_progress: FormatDownloadCallback | None = None,
    ):
        self.filepath = filepath
        self.format = format
        self.duration = duration
        self.progress = on_progress

    async def download(self):
        try:
            return await HttpxFormatDownloader(
                self.filepath, self.format, self.duration, self.progress
            ).download()
        except DownloadError as e:
            if e.status_code == 403:
                return await YDLFormatDownloader(
                    self.filepath, self.format, self.progress
                ).download()

            raise
