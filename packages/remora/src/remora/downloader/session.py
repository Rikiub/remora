from dataclasses import dataclass

import anyio
from httpx import AsyncClient

from remora._http import build_httpx_client  # noqa: F401
from remora._ydl import NetworkContext
from remora.models.options import DownloadOptions, NetworkOptions


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
    ydl_context: NetworkContext
