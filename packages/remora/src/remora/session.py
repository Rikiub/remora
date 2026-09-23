from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Self

import anyio
import httpx
from httpx import AsyncClient
from httpx_curl_cffi import AsyncCurlTransport
from typing_extensions import override

from remora import _ydl
from remora.constants import DEFAULT_MEDIA_CONCURRENCY, DEFAULT_POSTPROCESS_CONCURRENCY
from remora.models.options import DownloadOptions, NetworkOptions

__all__ = ["Session"]


@dataclass(slots=True)
class Session(anyio.AsyncContextManagerMixin):
    network_options: NetworkOptions
    download_options: DownloadOptions

    ydl_session: _ydl.Session
    httpx_client: AsyncClient

    extract_limiter: anyio.CapacityLimiter
    download_limiter: anyio.CapacityLimiter
    postprocess_limiter: anyio.CapacityLimiter

    @classmethod
    def create(
        cls,
        network_options: NetworkOptions | None = None,
        download_options: DownloadOptions | None = None,
        download_limit: float | None = None,
        extract_limit: float | None = None,
        postprocess_limit: float | None = None,
    ) -> Self:
        network_options = network_options or NetworkOptions()
        download_options = download_options or DownloadOptions()

        return cls(
            network_options=network_options,
            download_options=download_options,
            ydl_session=_ydl.Session.from_options(network_options),
            httpx_client=build_httpx_client(network_options),
            extract_limiter=anyio.CapacityLimiter(
                extract_limit or DEFAULT_MEDIA_CONCURRENCY
            ),
            download_limiter=anyio.CapacityLimiter(
                download_limit or DEFAULT_MEDIA_CONCURRENCY
            ),
            postprocess_limiter=anyio.CapacityLimiter(
                postprocess_limit or DEFAULT_POSTPROCESS_CONCURRENCY
            ),
        )

    async def close(self) -> None:
        self.ydl_session.close()
        await self.httpx_client.aclose()

    @override
    @asynccontextmanager
    async def __asynccontextmanager__(self) -> AsyncGenerator[Self, None]:
        try:
            yield self
        finally:
            await self.close()


def build_httpx_client(
    network_options: NetworkOptions,
    max_connections: int | None = None,
) -> httpx.AsyncClient:
    """Builds a configured httpx client from `NetworkOptions`."""
    network_options = network_options or NetworkOptions()

    transport = None
    if network_options.impersonate:
        transport = AsyncCurlTransport(impersonate=network_options.impersonate)  # ty: ignore[invalid-argument-type]

    # Parse global session cookies
    cookies = None
    if c := network_options.cookies:
        cookies = httpx.Cookies()
        for cookie in c:
            cookies.set(
                name=cookie.name,
                value=cookie.value,
                domain=cookie.domain,
                path=cookie.path,
            )

    return httpx.AsyncClient(
        cookies=cookies,
        proxy=str(network_options.proxy) if network_options.proxy else None,
        transport=transport,
        follow_redirects=True,
        limits=httpx.Limits(max_connections=max_connections),
    )
