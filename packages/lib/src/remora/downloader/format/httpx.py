import asyncio
from pathlib import Path
from urllib.parse import urljoin

import httpx
import aiofiles

from remora.exceptions import DownloadError
from remora.models.format.types import Format
from remora.models.progress.format import FormatDownloadCallback, FormatState
from remora.types import StrPath


class HttpxFormatDownloader:
    def __init__(
        self,
        filepath: StrPath,
        format: Format,
        duration: float | None = None,
        on_progress: FormatDownloadCallback | None = None,
    ):
        self.filepath = Path(filepath)
        self.format = format
        self.chunks = 8
        self.max_retries = 3
        self.progress = on_progress
        self.duration = duration
        self.format_state = FormatState()

    async def download(self) -> Path:
        try:
            async with httpx.AsyncClient(
                headers=self._get_headers(),
                cookies=self._get_cookies(),
                follow_redirects=True,
                timeout=None,
            ) as client:
                if self.format.protocol in (
                    "m3u8",
                    "m3u8_native",
                    "http_dash_segments",
                ):
                    await self._download_fragments(client)
                else:
                    await self._download_multi_part(client)
        except Exception as e:
            status_code = 0

            if isinstance(e, httpx.HTTPStatusError):
                status_code = e.response.status_code

            raise DownloadError(str(e), status_code=status_code) from e

        return await self._move_file()

    async def _download_multi_part(self, client: httpx.AsyncClient):
        # Check if the server explicitly supports ranges
        async with client.stream("GET", str(self.format.url)) as res:
            res.raise_for_status()
            supports_range: bool = res.headers.get("Accept-Ranges") == "bytes"
            total_size = int(res.headers.get("Content-Length", 0))

        # Determine chunks: Use user preference OR 1 if ranges aren't supported
        # Also use 1 if total_size is unknown (0)
        chunks = self.chunks if (supports_range and total_size) else 1

        # Calculate filesize
        if total_size:
            self.format_state.total_bytes = total_size
        else:
            total = self.format.filesize or 0

            if not total and self.format.bitrate and self.duration:
                total = int((self.format.bitrate * 1000 * self.duration) / 8)

            self.format_state.total_bytes = total

        chunk_size = total_size // chunks
        tasks = []
        part_files: list[Path] = []

        for i in range(chunks):
            start = i * chunk_size
            end = (i + 1) * chunk_size - 1 if i < chunks - 1 else total_size - 1

            part_path = Path(f"{self.filepath}.part{i}")
            part_files.append(part_path)

            tasks.append(self._save_range(client, start, end, part_path))

        await asyncio.gather(*tasks)

        async with aiofiles.open(self.filepath, "wb") as final_file:
            for part in part_files:
                async with aiofiles.open(part, "rb") as pf:
                    await final_file.write(await pf.read())
                part.unlink()

    async def _download_fragments(self, client: httpx.AsyncClient):
        response = await client.get(str(self.format.url))
        urls = [
            urljoin(str(self.format.url), line.strip())
            for line in response.text.splitlines()
            if line.strip() and not line.startswith("#")
        ]

        # HLS is sequential; we write directly to the main file
        async with aiofiles.open(self.filepath, "wb") as f:
            for url in urls:
                data = await self._fetch_with_retry(client, url)
                await f.write(data)
                await self._update_progress(len(data))

    async def _save_range(
        self,
        client: httpx.AsyncClient,
        start: int,
        end: int | None,
        path: Path,
    ):
        """Downloads a specific byte range to a file with resume support."""

        written = 0

        for attempt in range(self.max_retries):
            try:
                current_start = start + written
                headers = self._get_headers()

                if end:
                    if current_start > end:
                        return
                    headers["Range"] = f"bytes={current_start}-{end}"

                async with client.stream(
                    "GET",
                    str(self.format.url),
                    headers=headers,
                ) as res:
                    res.raise_for_status()

                    async with aiofiles.open(path, "ab" if written > 0 else "wb") as f:
                        async for chunk in res.aiter_bytes():
                            await f.write(chunk)
                            written += len(chunk)
                            await self._update_progress(len(chunk))
                return
            except Exception:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)

    async def _fetch_with_retry(self, client: httpx.AsyncClient, url: str) -> bytes:
        """Generic retry fetch for small fragments."""

        for attempt in range(self.max_retries):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.content
            except Exception:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)
        return b""

    async def _move_file(self) -> Path:
        old_file = self.filepath
        new_file = old_file.with_suffix(f".{self.format.extension}")
        return await asyncio.to_thread(old_file.rename, new_file)

    async def _update_progress(self, size: int):
        self.format_state.downloaded_bytes += size

        if self.format_state.downloaded_bytes > self.format_state.total_bytes:
            self.format_state.total_bytes = self.format_state.downloaded_bytes

        if self.progress:
            await self.progress(self.format_state)

    def _get_headers(self) -> dict[str, str]:
        headers = {
            **self.format.http_headers,
            "Accept-Encoding": "identity",
        }
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
