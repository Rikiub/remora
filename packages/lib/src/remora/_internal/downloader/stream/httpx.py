import pathlib
from urllib.parse import urljoin

import anyio
import httpx
from anyio import Path
from loguru import logger
from typing_extensions import override

from remora._internal.downloader.stream.base import BaseStreamDownloader
from remora.exceptions import DownloaderError
from remora.models.event import (
    StreamCompleted,
    StreamContinuous,
    StreamEvent,
    StreamSegmented,
)
from remora.models.protocol import Protocol
from remora.models.stream import SizeType, Stream
from remora.types import DEFAULT_RETRIES, StrPath


class HttpxStreamDownloader(BaseStreamDownloader[StreamEvent]):
    SUPPORTED_PROTOCOLS = frozenset(
        {
            Protocol.HTTP,
            Protocol.HTTPS,
            Protocol.M3U8,
            Protocol.M3U8_NATIVE,
            Protocol.HTTP_DASH_SEGMENTS,
            Protocol.HTTP_DASH_SEGMENTS_GENERATOR,
        }
    )

    def __init__(
        self,
        output_path: StrPath,
        stream: Stream,
        retries: int = DEFAULT_RETRIES,
        max_workers: int = 8,
    ):
        super().__init__(output_path, stream, retries, buffer_size=20)

        # Workers
        self.max_workers = max_workers
        self.limiter = anyio.CapacityLimiter(max_workers)

        # Progress
        self.is_continuous = False

        self.downloaded_bytes = 0
        self.total_bytes = self.stream.size_bytes
        self.size_type: SizeType = self.stream.size_type

        self.current_segment = 0
        self.total_segments = 0

        # Log
        self._log_stream()

    @override
    async def _on_finally(self):
        await self.client.aclose()

    @override
    async def _run_pipeline(self) -> None:
        self.client = httpx.AsyncClient(
            headers=self._get_headers(),
            cookies=self._get_cookies(),
            follow_redirects=True,
        )

        protocol = Protocol(self.stream.protocol)
        logger.debug('Stream protocol is "{}"', str(protocol))

        async with self.client:
            try:
                if protocol.is_segmented:
                    logger.debug("Downloading stream segments")
                    path = await self._download_segments()

                elif protocol in (Protocol.HTTP, Protocol.HTTPS):
                    logger.debug("Downloading stream as http")

                    self.is_continuous = True
                    path = await self._download_multi_part()

                else:
                    raise TypeError(
                        f"Unable to handle protocol: {self.stream.protocol}"
                    )
            except* (httpx.HTTPError, OSError, ValueError, TypeError) as eg:
                error = eg.exceptions[0]
                status_code = 0

                if isinstance(error, httpx.HTTPStatusError):
                    status_code = error.response.status_code

                raise DownloaderError(str(error), status_code=status_code) from error

        path = await self._fix_extension(path)
        self.file_path = path

        await self._emit(StreamCompleted(file_path=pathlib.Path(self.file_path)))
        await self._on_cancelled()

    async def _download_multi_part(self) -> Path:
        async with self.client.stream(
            "GET",
            str(self.stream.url),
            headers={"Range": "bytes=0-0"},
        ) as res:
            res.raise_for_status()

            if supports_range := res.status_code == 206:
                logger.debug("Server supports range; downloading in parallel")

                content_range = res.headers.get("Content-Range")
                size = int(content_range.split("/")[-1])

                self.total_bytes = size
                self.size_type = "exact"

                # Pre-allocate
                async with await self.file_path.open("wb") as f:
                    await f.truncate(self.total_bytes)
            else:
                logger.debug("Server don't supports range; downloading single file")

                content_length = res.headers.get("Content-Length")
                self.total_bytes = int(content_length) if content_length else None
                self.size_type = "estimated" if self.total_bytes else "unknown"

            logger.debug(
                "Total file size: {file_size} ({size_type})",
                file_size=self.total_bytes,
                size_type=self.size_type,
            )

            workers = self.max_workers if (supports_range and self.total_bytes) else 1

            async with anyio.create_task_group() as tg:
                if supports_range and self.total_bytes:
                    # Multi-part parallel download
                    chunk_size = self.total_bytes // workers

                    for i in range(workers):
                        start = i * chunk_size
                        end = (
                            (i + 1) * chunk_size - 1
                            if i < workers - 1
                            else self.total_bytes - 1
                        )

                        tg.start_soon(
                            self._save_range,
                            self.file_path,
                            str(self.stream.url),
                            start,
                            end,
                            True,
                        )
                else:
                    # Single-stream download
                    tg.start_soon(
                        self._save_range,
                        self.file_path,
                        str(self.stream.url),
                        0,
                        None,
                        False,
                    )

        return self.file_path

    async def _download_segments(self) -> Path:
        res = await self.client.get(str(self.stream.url))
        res.raise_for_status()

        urls = [
            urljoin(str(self.stream.url), line.strip())
            for line in res.text.splitlines()
            if line.strip() and not line.startswith("#")
        ]

        part_files: list[Path] = []
        logger.debug(
            "{fragments_total} fragments will be downloaded in parallel",
            fragments_total=len(urls),
        )

        async with anyio.create_task_group() as tg:
            for index, url in enumerate(urls):
                part = self._gen_part_file(index)
                await part.touch()
                part_files.append(part)

                tg.start_soon(
                    self._save_range,
                    part,
                    url,
                    0,
                    None,
                    False,
                )

        file = await self._build_parts(part_files)
        return file

    async def _save_range(
        self,
        path: Path,
        url: str,
        start: int = 0,
        end: int | None = None,
        is_continuous: bool = False,
    ):
        """Downloads a specific byte range to a file with resume support."""

        async with self.limiter:
            if end:
                logger.debug(
                    "Downloading range: {range_start}/{range_end}",
                    range_start=start,
                    range_end=end,
                )

            downloaded = 0

            # 'r+b' for shared files, 'ab' for part files
            mode = "r+b" if is_continuous else "ab"

            async with await path.open(mode) as f:
                for attempt in range(self.retries):
                    if is_continuous:
                        current_start = start + downloaded
                    else:
                        stats = await path.stat()
                        current_start = start + stats.st_size

                    headers = {"Range": f"bytes={current_start}-{end}"} if end else {}

                    try:
                        async with self.client.stream(
                            "GET",
                            url,
                            headers=headers,
                        ) as res:
                            res.raise_for_status()

                            if is_continuous:
                                await f.seek(current_start)

                            async for chunk in res.aiter_bytes():
                                await f.write(chunk)

                                downloaded += len(chunk)
                                self.downloaded_bytes += len(chunk)

                                await self._update_progress()

                            if end:
                                logger.debug(
                                    "Downloaded range: {range_start}/{range_end}",
                                    range_start=start,
                                    range_end=end,
                                )

                            return
                    except Exception:
                        if attempt == self.retries - 1:
                            raise
                        await anyio.sleep(2**attempt)

    async def _build_parts(self, parts: list[Path]) -> Path:
        async with await self.file_path.open("wb") as final_file:
            for part in parts:
                async with await part.open("rb") as pf:
                    data = await pf.read()
                    await final_file.write(data)
                await part.unlink()
        return self.file_path

    async def _fix_extension(self, path: Path) -> Path:
        new_file = path.with_suffix(f".{self.stream.extension}")
        return await path.rename(new_file)

    async def _update_progress(self):
        if self.total_bytes and (self.downloaded_bytes > self.total_bytes):
            self.total_bytes = self.downloaded_bytes

        # Send event to top function
        if self.is_continuous:
            await self._emit(
                StreamContinuous(
                    downloaded_bytes=self.downloaded_bytes,
                    total_bytes=self.total_bytes,
                )
            )
        else:
            await self._emit(
                StreamSegmented(
                    downloaded_bytes=self.downloaded_bytes,
                    current_segment=self.current_segment,
                    total_segments=self.total_segments,
                )
            )

    def _get_headers(self) -> dict[str, str] | None:
        return self.stream.request_context.headers

    def _get_cookies(self) -> dict[str, str]:
        cookie_dict = {}
        if not self.stream.request_context.cookies:
            return cookie_dict

        # 1. Clean the string and split
        # yt-dlp cookie strings often have multiple cookies separated by '; '
        parts = self.stream.request_context.cookies.split(";")

        for part in parts:
            if "=" not in part:
                continue

            key, val = part.split("=", 1)
            key = key.strip()
            val = val.strip()

            # 2. Skip metadata attributes entirely
            # We only want the actual data keys
            if key.lower() in (
                "domain",
                "path",
                "expires",
                "secure",
                "httponly",
                "samesite",
            ):
                continue

            cookie_dict[key] = val

        return cookie_dict

    def _gen_part_file(self, index) -> Path:
        return Path(f"{self.file_path}.part{index}")
