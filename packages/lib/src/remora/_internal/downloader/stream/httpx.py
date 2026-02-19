import pathlib
from collections.abc import AsyncIterable
from urllib.parse import urljoin

import anyio
import httpx
from anyio import Path
from typing_extensions import override

from remora._internal.downloader.stream.base import BaseStreamDownloader
from remora.exceptions import DownloadError
from remora.models.event.stream import CompletedStream, DownloadingStream, StreamEvent
from remora.models.stream.item import Stream
from remora.types import DEFAULT_RETRIES, StrPath

_HTTP_PROTOCOLS = {
    "http",
    "https",
}
_LIST_PROTOCOLS = {
    "m3u8",
    "m3u8_native",
    "http_dash_segments",
}


class HttpxStreamDownloader(BaseStreamDownloader):
    SUPPORTED_PROTOCOLS = {*_HTTP_PROTOCOLS, *_LIST_PROTOCOLS}

    def __init__(
        self,
        output_path: StrPath,
        stream: Stream,
        retries: int = DEFAULT_RETRIES,
        max_workers: int = 8,
        duration: float | None = None,
    ):
        super().__init__(output_path, stream, retries)
        self.duration = duration

        # Calculate file size
        total = self.stream.size or 0

        if not total and self.stream.bitrate and self.duration:
            total = int((self.stream.bitrate * 1000 * self.duration) / 8)

        self.event = DownloadingStream(total=total)
        self.file_size = total

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
        ](20)

        async with receive_stream:
            async with anyio.create_task_group() as tg:
                tg.start_soon(self._execute_download)

                async for event in receive_stream:
                    yield event

                yield CompletedStream(file_path=pathlib.Path(self.file_path))

    async def _execute_download(self):
        async with self._send_stream:
            try:
                async with self.client:
                    if self.stream.protocol in _HTTP_PROTOCOLS:
                        path = await self._download_multi_part()
                    elif self.stream.protocol in _LIST_PROTOCOLS:
                        path = await self._download_fragments()
                    else:
                        raise TypeError(
                            f"Unable to handle protocol: {self.stream.protocol}"
                        )
            except* (httpx.HTTPStatusError, httpx.RequestError) as eg:
                error = eg.exceptions[0]
                status_code = 0

                if isinstance(error, httpx.HTTPStatusError):
                    status_code = error.response.status_code

                raise DownloadError(str(error), status_code=status_code) from error

            path = await self._fix_extension(path)
            self.file_path = path

    async def _download_multi_part(self) -> Path:
        # Check if the server explicitly supports ranges
        async with self.client.stream("GET", str(self.stream.url)) as res:
            res.raise_for_status()
            supports_range: bool = res.headers.get("Accept-Ranges") == "bytes"
            remote_total_size = int(res.headers.get("Content-Length", 0))

        # Fix file size
        if remote_total_size:
            self.file_size = remote_total_size
            self.event.total = remote_total_size

        # Determine chunks: Use user preference OR 1 if ranges aren't supported
        # Also use 1 if total_size is unknown (0)
        workers = self.max_workers if (supports_range and self.file_size) else 1
        chunk_size = self.file_size // workers

        # PRE-ALLOCATE
        async with await self.file_path.open("wb") as f:
            await f.truncate(self.file_size)

        async with anyio.create_task_group() as tg:
            for i in range(workers):
                start = i * chunk_size
                end = (
                    (i + 1) * chunk_size - 1 if i < workers - 1 else self.file_size - 1
                )

                tg.start_soon(
                    self._save_range,
                    self.file_path,
                    str(self.stream.url),
                    start,
                    end,
                    True,
                )

        return self.file_path

    async def _download_fragments(self) -> Path:
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
                await part.touch()

                part_files.append(part)

                tg.start_soon(
                    self._save_range,
                    part,
                    url,
                    0,
                    0,
                    False,
                )

        file = await self._build_parts(part_files)
        return file

    async def _save_range(
        self,
        path: Path,
        url: str,
        start: int = 0,
        end: int = 0,
        is_parallel: bool = False,
    ):
        """Downloads a specific byte range to a file with resume support."""

        async with self.limiter:
            downloaded = 0

            for attempt in range(self.retries):
                if is_parallel:
                    current_start = start + downloaded
                else:
                    stats = await path.stat()
                    current_start = start + stats.st_size

                if end and current_start > end:
                    break

                headers = {"Range": f"bytes={current_start}-{end}"} if end else {}

                try:
                    async with self.client.stream(
                        "GET",
                        url,
                        headers=headers,
                    ) as res:
                        res.raise_for_status()

                        # 'r+b' for shared files, 'ab' for part files
                        mode = "r+b" if is_parallel else "ab"

                        async with await path.open(mode) as f:
                            if is_parallel:
                                await f.seek(current_start)

                            async for chunk in res.aiter_bytes():
                                await f.write(chunk)

                                downloaded += len(chunk)
                                await self._update_progress(len(chunk))
                except (httpx.HTTPStatusError, httpx.RequestError):
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

    async def _update_progress(self, size: int):
        event = self.event
        event.downloaded += size

        if event.downloaded > event.total:
            event.total = event.downloaded

        # Send event to top function
        await self._send_stream.send(event)

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
        return Path(f"{self.file_path}.part{index}")
