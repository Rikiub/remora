import pathlib
from typing import AsyncIterable
from urllib.parse import urljoin

import anyio
import httpx
from anyio import Path
from remora.downloader.stream.base import DEFAULT_RETRIES, BaseStreamDownloader
from remora.exceptions import DownloadError
from remora.models.stream.types import Stream
from remora.models.event.stream import (
    FinishedStream,
    DownloadingStream,
    StreamEvent,
)
from remora.types import StrPath
from typing_extensions import override

_HTTP_PROTOCOLS = [
    "http",
    "https",
]
_LIST_PROTOCOLS = [
    "m3u8",
    "m3u8_native",
    "http_dash_segments",
]


class HttpxStreamDownloader(BaseStreamDownloader):
    SUPPORTED_PROTOCOLS = [*_HTTP_PROTOCOLS, *_LIST_PROTOCOLS]

    def __init__(
        self,
        filepath: StrPath,
        stream: Stream,
        retries: int = DEFAULT_RETRIES,
        max_workers: int = 8,
        duration: float | None = None,
    ):
        super().__init__(filepath, stream, retries)
        self.duration = duration

        # Calculate filesize
        total = self.stream.filesize or 0

        if not total and self.stream.bitrate and self.duration:
            total = int((self.stream.bitrate * 1000 * self.duration) / 8)

        self.event = DownloadingStream(total_bytes=total)

        # Workers
        self.max_workers = max_workers
        self.limiter = anyio.CapacityLimiter(max_workers)

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            headers=self._get_headers(),
            cookies=self._get_cookies(),
            follow_redirects=True,
            timeout=None,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    @override
    async def download(self) -> AsyncIterable[StreamEvent]:  # type: ignore
        self._log_stream()
        self._send_stream, receive_stream = anyio.create_memory_object_stream[
            StreamEvent
        ](max_buffer_size=self.max_workers)

        async with receive_stream:
            async with anyio.create_task_group() as tg:
                tg.start_soon(self._execute_download)

                async for event in receive_stream:
                    yield event

                yield FinishedStream(filepath=pathlib.Path(self.filepath))

    async def _execute_download(self):
        async with self._send_stream:
            try:
                async with self.client:
                    if self.stream.protocol in _HTTP_PROTOCOLS:
                        parts = await self._download_multi_part()
                    elif self.stream.protocol in _LIST_PROTOCOLS:
                        parts = await self._download_fragments()
                    else:
                        raise TypeError(
                            f"Unable to handle protocol: {self.stream.protocol}"
                        )
            except Exception as error:
                status_code = 0

                if isinstance(error, httpx.HTTPStatusError):
                    status_code = error.response.status_code

                raise DownloadError(str(error), status_code=status_code) from error

            filepath = await self._build_parts(parts)
            filepath = await self._rename_extension(filepath)
            self.filepath = filepath

    async def _download_multi_part(self) -> list[Path]:
        # Check if the server explicitly supports ranges
        async with self.client.stream("GET", str(self.stream.url)) as res:
            res.raise_for_status()
            supports_range: bool = res.headers.get("Accept-Ranges") == "bytes"
            total_size = int(res.headers.get("Content-Length", 0))

        # Determine chunks: Use user preference OR 1 if ranges aren't supported
        # Also use 1 if total_size is unknown (0)
        workers = self.max_workers if (supports_range and total_size) else 1

        # Calculate filesize
        if total_size:
            self.event.total_bytes = total_size

        chunk_size = total_size // workers
        part_files: list[Path] = []

        async with anyio.create_task_group() as tg:
            for i in range(workers):
                start = i * chunk_size
                end = (i + 1) * chunk_size - 1 if i < workers - 1 else total_size - 1

                part = self._gen_part_file(i)
                part_files.append(part)

                tg.start_soon(
                    self._save_range,
                    part,
                    str(self.stream.url),
                    start,
                    end,
                )

        return part_files

    async def _download_fragments(self) -> list[Path]:
        response = await self.client.get(str(self.stream.url))
        urls = [
            urljoin(str(self.stream.url), line.strip())
            for line in response.text.splitlines()
            if line.strip() and not line.startswith("#")
        ]

        part_files: list[Path] = []

        async with anyio.create_task_group() as tg:
            for index, url in enumerate(urls):
                part = self._gen_part_file(index)
                part_files.append(part)

                tg.start_soon(
                    self._save_range,
                    part,
                    url,
                )

        return part_files

    async def _save_range(
        self,
        path: Path,
        url: str,
        start: int = 0,
        end: int = 0,
    ):
        """Downloads a specific byte range to a file with resume support."""

        async with self.limiter:
            if not await path.exists():
                await path.touch()

            for attempt in range(self.retries):
                stats = await path.stat()
                current_file_size = stats.st_size
                current_start = start + current_file_size

                if end and current_start > end:
                    break

                headers = {}
                if end:
                    headers |= {"Range": f"bytes={current_start}-{end}"}

                try:
                    async with self.client.stream(
                        "GET",
                        url,
                        headers=headers,
                    ) as res:
                        res.raise_for_status()

                        async with await path.open("ab") as f:
                            async for chunk in res.aiter_bytes():
                                await f.write(chunk)
                                await self._update_progress(len(chunk))
                except Exception:
                    if attempt == self.retries - 1:
                        raise
                    await anyio.sleep(2**attempt)

    async def _build_parts(self, parts: list[Path]) -> Path:
        async with await self.filepath.open("wb") as final_file:
            for part in parts:
                async with await part.open("rb") as pf:
                    data = await pf.read()
                    await final_file.write(data)
                await part.unlink()
        return self.filepath

    async def _rename_extension(self, filepath: Path) -> Path:
        new_file = filepath.with_suffix(f".{self.stream.extension}")
        return await filepath.rename(new_file)

    async def _update_progress(self, size: int):
        event = self.event
        event.downloaded_bytes += size

        if event.downloaded_bytes > event.total_bytes:
            event.total_bytes = event.downloaded_bytes

        # Send event to top function
        self._send_stream.send_nowait(event)

    def _get_headers(self) -> dict[str, str]:
        headers = self.stream.http_headers
        return headers

    def _get_cookies(self) -> dict[str, str]:
        cookie_dict = {}
        if not self.stream.cookies:
            return cookie_dict

        # 1. Clean the string and split
        # yt-dlp cookie strings often have multiple cookies separated by '; '
        parts = self.stream.cookies.split(";")

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
        return Path(f"{self.filepath}.part{index}")
