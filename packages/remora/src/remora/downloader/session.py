from dataclasses import dataclass

import anyio
import httpx
from httpx import AsyncClient
from httpx_curl_cffi import AsyncCurlTransport

from remora._ydl import YDLNetworkContext
from remora.constants import DEFAULT_MEDIA_CONCURRENCY, DEFAULT_POSTPROCESS_CONCURRENCY
from remora.models.options import DownloadOptions, NetworkOptions

__all__ = ["DownloadSession", "build_httpx_client"]


@dataclass(slots=True)
class Limiters:
    extract: anyio.CapacityLimiter
    download: anyio.CapacityLimiter
    postprocess: anyio.CapacityLimiter


@dataclass(slots=True)
class Options:
    download: DownloadOptions
    network: NetworkOptions


@dataclass(slots=True)
class DownloadSession:
    options: Options
    limiters: Limiters
    httpx_client: AsyncClient
    ydl_context: YDLNetworkContext

    @classmethod
    def create(
        cls,
        network_options: NetworkOptions | None = None,
        download_options: DownloadOptions | None = None,
        download_limit: float | None = None,
        extract_limit: float | None = None,
        postprocess_limit: float | None = None,
    ):
        download_options = download_options or DownloadOptions()
        network_options = network_options or NetworkOptions()

        return cls(
            options=Options(
                download=download_options,
                network=network_options,
            ),
            limiters=Limiters(
                extract=anyio.CapacityLimiter(
                    extract_limit or DEFAULT_MEDIA_CONCURRENCY
                ),
                download=anyio.CapacityLimiter(
                    download_limit or DEFAULT_MEDIA_CONCURRENCY
                ),
                postprocess=anyio.CapacityLimiter(
                    postprocess_limit or DEFAULT_POSTPROCESS_CONCURRENCY
                ),
            ),
            httpx_client=build_httpx_client(network_options),
            ydl_context=YDLNetworkContext.from_options(network_options),
        )


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

    limits = httpx.Limits(max_connections=max_connections)

    return httpx.AsyncClient(
        cookies=cookies,
        proxy=str(network_options.proxy) if network_options.proxy else None,
        transport=transport,
        follow_redirects=True,
        limits=limits,
    )
