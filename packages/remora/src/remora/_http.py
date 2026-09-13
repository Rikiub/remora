import httpx
from httpx_curl_cffi import AsyncCurlTransport

from remora.models.options import NetworkOptions

__all__ = ["build_httpx_client"]


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
