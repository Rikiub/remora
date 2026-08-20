from pathlib import Path

from anyio.to_thread import run_sync
from loguru import logger
from typing_extensions import override

from remora._internal.downloader.stream.base import BaseStreamDownloader
from remora.constants import DEFAULT_RETRIES
from remora.exceptions import DownloaderError
from remora.models.progress import (
    StreamCompleted,
    StreamContinuous,
    StreamSegmented,
    StreamState,
)
from remora.models.protocol import Protocol
from remora.models.stream import Stream
from remora.models.types import StrPath


class YDLStreamDownloader(BaseStreamDownloader[StreamState]):
    SUPPORTED_PROTOCOLS = frozenset(Protocol)

    def __init__(
        self,
        output_path: StrPath,
        stream: Stream,
        retries: int = DEFAULT_RETRIES,
    ):
        super().__init__(output_path, stream, retries=retries)

        self.downloaded_bytes = 0
        self.total_bytes = 0

        self.current_segment = 0
        self.total_segments = 0

    @override
    async def _run_pipeline(self) -> None:
        from remora._internal.ydl.types import DEFAULT_IMPERSONATE_TARGET

        try:
            path = await self._downloader()
        except DownloaderError as error:
            if error.status_code == 403:
                impersonate = DEFAULT_IMPERSONATE_TARGET
                logger.debug(
                    'HTTP 403 Forbidden: Retrying with "{impersonate}" impersonate target',
                    impersonate=impersonate,
                )
                path = await self._downloader(impersonate=impersonate)
            else:
                raise

        await self._emit(StreamCompleted(file_path=path))

    async def _downloader(self, impersonate: str | None = None) -> Path:
        from remora._internal.ydl.downloader import download_format

        return await run_sync(
            download_format,
            self.file_path,
            self.stream._to_ydl_dict(),
            self._ydl_progress,
            self.retries,
            impersonate,
        )

    def _ydl_progress(self, data: dict) -> None:
        """`YT-DLP` progress hook, but stable and without issues."""

        d = data

        speed = 0
        elapsed = 0

        match d["status"]:
            case "downloading":
                downloaded_bytes = d.get("downloaded_bytes") or 0
                total_bytes = (
                    d.get("total_bytes") or d.get("total_bytes_estimate") or None
                )

                self.current_segment = d.get("fragment_index")
                self.total_segments = d.get("fragment_count")

                if total_bytes:
                    self.downloaded_bytes = max(self.downloaded_bytes, downloaded_bytes)
                    self.total_bytes = max(self.total_bytes, total_bytes)

                speed = d.get("speed") or 0
                elapsed = d.get("elapsed") or 0
            case "finished":
                self.downloaded_bytes = self.total_bytes

        if self.current_segment:
            self._emit_nowait(
                StreamSegmented(
                    current_segment=self.current_segment,
                    total_segments=self.total_segments,
                    downloaded_bytes=self.downloaded_bytes,
                    speed=speed,
                    elapsed=elapsed,
                )
            )
        else:
            self._emit_nowait(
                StreamContinuous(
                    downloaded_bytes=self.downloaded_bytes,
                    total_bytes=self.total_bytes or None,
                    speed=speed,
                    elapsed=elapsed,
                )
            )
