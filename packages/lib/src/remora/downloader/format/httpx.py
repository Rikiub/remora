from typing_extensions import override
from urllib.parse import urljoin

import anyio
from anyio import Path
import httpx

from remora.downloader.format.base import DEFAULT_RETRIES, BaseFormatDownloader
from remora.exceptions import DownloadError
from remora.models.format.types import Format
from remora.models.progress.format import FormatDownloadCallback
from remora.types import StrPath

_HTTP_PROTOCOLS = [
    "http",
    "https",
]
_LIST_PROTOCOLS = [
    "m3u8",
    "m3u8_native",
    "http_dash_segments",
]


class HttpxFormatDownloader(BaseFormatDownloader):
    SUPPORTED_PROTOCOLS = [*_HTTP_PROTOCOLS, *_LIST_PROTOCOLS]

    def __init__(
        self,
        filepath: StrPath,
        format: Format,
        on_progress: FormatDownloadCallback | None = None,
        retries: int = DEFAULT_RETRIES,
        max_workers: int = 8,
        duration: float | None = None,
    ):
        super().__init__(filepath, format, on_progress, retries)
        self.duration = duration

        # Calculate filesize
        total = self.format.filesize or 0

        if not total and self.format.bitrate and self.duration:
            total = int((self.format.bitrate * 1000 * self.duration) / 8)

        self.format_state.total_bytes = total

        # Workers
        self.max_workers = max_workers
        self.semaphore = anyio.Semaphore(self.max_workers)

    @override
    async def download(self) -> Path:
        try:
            async with httpx.AsyncClient(
                headers=self._get_headers(),
                cookies=self._get_cookies(),
                follow_redirects=True,
                timeout=None,
            ) as client:
                if self.format.protocol in _HTTP_PROTOCOLS:
                    parts = await self._download_multi_part(client)
                elif self.format.protocol in _LIST_PROTOCOLS:
                    parts = await self._download_fragments(client)
                else:
                    raise DownloadError(
                        f"Unable to handle protocol: {self.format.protocol}"
                    )
        except Exception as e:
            status_code = 0

            if isinstance(e, httpx.HTTPStatusError):
                status_code = e.response.status_code

            raise DownloadError(str(e), status_code=status_code) from e

        filepath = await self._build_parts(parts)
        filepath = await self._rename_extension(filepath)
        return filepath

    async def _download_multi_part(self, client: httpx.AsyncClient) -> list[Path]:
        # Check if the server explicitly supports ranges
        async with client.stream("GET", str(self.format.url)) as res:
            res.raise_for_status()
            supports_range: bool = res.headers.get("Accept-Ranges") == "bytes"
            total_size = int(res.headers.get("Content-Length", 0))

        # Determine chunks: Use user preference OR 1 if ranges aren't supported
        # Also use 1 if total_size is unknown (0)
        workers = self.max_workers if (supports_range and total_size) else 1

        # Calculate filesize
        if total_size:
            self.format_state.total_bytes = total_size

        chunk_size = total_size // workers
        part_files = []

        async with anyio.create_task_group() as tg:
            for i in range(workers):
                start = i * chunk_size
                end = (i + 1) * chunk_size - 1 if i < workers - 1 else total_size - 1

                tg.start_soon(
                    self._save_range,
                    client,
                    self._gen_part_file(i),
                    part_files,
                    str(self.format.url),
                    start,
                    end,
                )

        return part_files

    async def _download_fragments(self, client: httpx.AsyncClient) -> list[Path]:
        response = await client.get(str(self.format.url))
        urls = [
            urljoin(str(self.format.url), line.strip())
            for line in response.text.splitlines()
            if line.strip() and not line.startswith("#")
        ]

        part_files = []

        async with anyio.create_task_group() as tg:
            for index, url in enumerate(urls):
                tg.start_soon(
                    self._save_range,
                    client,
                    self._gen_part_file(index),
                    part_files,
                    url,
                )

        return part_files

    async def _save_range(
        self,
        client: httpx.AsyncClient,
        path: Path,
        part_files: list[Path],
        url: str,
        start: int = 0,
        end: int = 0,
    ):
        """Downloads a specific byte range to a file with resume support."""

        async with self.semaphore:
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
                    async with client.stream(
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
        return part_files.append(path)

    async def _build_parts(self, parts: list[Path]) -> Path:
        async with await self.filepath.open("wb") as final_file:
            for part in parts:
                async with await part.open("rb") as pf:
                    data = await pf.read()
                    await final_file.write(data)
                await part.unlink()
        return self.filepath

    async def _rename_extension(self, filepath: Path) -> Path:
        new_file = filepath.with_suffix(f".{self.format.extension}")
        return await filepath.rename(new_file)

    async def _update_progress(self, size: int):
        state = self.format_state
        state.downloaded_bytes += size

        if state.downloaded_bytes > state.total_bytes:
            state.total_bytes = state.downloaded_bytes

        if self.progress:
            await self.progress(self.format_state)

    def _get_headers(self) -> dict[str, str]:
        headers = self.format.http_headers
        return headers

    def _get_cookies(self):
        cookie_dict = {}
        if not self.format.cookies:
            return cookie_dict

        # 1. Clean the string and split
        # yt-dlp cookie strings often have multiple cookies separated by '; '
        parts = self.format.cookies.split(";")

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
