import pathlib
from urllib.parse import urljoin

import anyio
import httpx
from anyio import Path
from loguru import logger
from typing_extensions import override

from remora._internal.downloader.stream.base import BaseStreamDownloader
from remora.exceptions import DownloaderError
from remora.models.progress import (
    StreamCompleted,
    StreamContinuous,
    StreamSegmented,
    StreamState,
)
from remora.models.protocol import Protocol
from remora.models.stream import SizeType, Stream
from remora.models.types import StrPath
from remora.types import DEFAULT_RETRIES


class HttpxStreamDownloader(BaseStreamDownloader[StreamState]):
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
        super().__init__(output_path, stream, retries)

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
    async def _on_exit(self):
        await self.client.aclose()

    @override
    async def _run_pipeline(self) -> None:
        self.client = httpx.AsyncClient(
            headers=self.stream.request_context.headers,
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
                status_code = None

                if isinstance(error, httpx.HTTPStatusError):
                    status_code = error.response.status_code

                raise DownloaderError(str(error), status_code=status_code) from error

        path = await self._fix_extension(path)
        self.file_path = path

        await self._emit(StreamCompleted(file_path=pathlib.Path(self.file_path)))

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
        urls: list[str] = []
        protocol = self.stream.protocol

        # Use pre-parsed fragments
        if fragments := self.stream.fragments:
            logger.debug("Using pre-parsed fragments")

            for frag in fragments:
                urls.append(str(frag.url))

        # HLS: Manual M3U8 Parsing
        elif protocol in (Protocol.M3U8, Protocol.M3U8_NATIVE):
            logger.debug("Manually parsing M3U8 manifest")

            res = await self.client.get(str(self.stream.url))
            res.raise_for_status()

            for line in res.text.splitlines():
                line = line.strip()
                if not line:
                    continue

                if line.startswith("#EXT-X-MAP:"):
                    start = line.find('URI="')
                    if start != -1:
                        start += 5
                        end = line.find('"', start)
                        if end != -1:
                            init_uri = line[start:end]
                            urls.append(urljoin(str(self.stream.url), init_uri))
                elif not line.startswith("#"):
                    urls.append(urljoin(str(self.stream.url), line))

        # DASH: Fail gracefully
        elif protocol in (
            Protocol.HTTP_DASH_SEGMENTS,
            Protocol.HTTP_DASH_SEGMENTS_GENERATOR,
        ):
            raise DownloaderError(
                f"Cannot manually parse {protocol.value} XML manifests."
                "Ensure 'fragments' info is passed to the `Stream` model."
            )
        else:
            raise TypeError(f"Unsupported segmented protocol: {protocol.value}")

        if not urls:
            raise DownloaderError("No segments found to download.")

        self.total_segments = len(urls)
        logger.debug(
            "{fragments_total} fragments will be downloaded in parallel",
            fragments_total=self.total_segments,
        )
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
            downloaded = 0

            # Support resuming part files across application restarts
            if not is_continuous:
                stats = await path.stat()
                downloaded = stats.st_size
                self.downloaded_bytes += downloaded

            # Use "r+b" universally
            async with await path.open("r+b") as f:
                for attempt in range(self.retries):
                    current_start = start + downloaded

                    # Formulate Range correctly even if end is None
                    headers = {}
                    if current_start > 0 or end is not None:
                        range_end = end if end is not None else ""
                        headers = {"Range": f"bytes={current_start}-{range_end}"}

                    try:
                        async with self.client.stream(
                            "GET",
                            url,
                            headers=headers,
                        ) as res:
                            res.raise_for_status()

                            # Handle server ignoring the Range request (returns 200 instead of 206)
                            if res.status_code == 200 and current_start > start:
                                self.downloaded_bytes -= downloaded
                                downloaded = 0
                                current_start = start
                                if not is_continuous:
                                    await f.truncate(0)

                            # Always seek to the correct write position
                            await f.seek(current_start)

                            async for chunk in res.aiter_bytes():
                                await f.write(chunk)
                                downloaded += len(chunk)
                                self.downloaded_bytes += len(chunk)

                                await self._update_progress()

                        # Update segment progress upon successful download
                        if not is_continuous:
                            self.current_segment += 1
                            await self._update_progress()

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

        # Send state to top function
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

    def _get_cookies(self) -> dict[str, str]:
        cookie_dict = {}
        if not self.stream.request_context.cookies:
            return cookie_dict

        # Clean the string and split
        # yt-dlp cookie strings often have multiple cookies separated by '; '
        parts = self.stream.request_context.cookies.split(";")

        for part in parts:
            if "=" not in part:
                continue

            key, val = part.split("=", 1)
            key = key.strip()
            val = val.strip()

            # Skip metadata attributes entirely
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
