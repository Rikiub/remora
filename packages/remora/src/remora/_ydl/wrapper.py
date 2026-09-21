from __future__ import annotations

import tempfile
from abc import ABC
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cached_property
from io import StringIO
from typing import TYPE_CHECKING, Any, Self

from anyio import ContextManagerMixin
from loguru import logger
from typing_extensions import override
from yt_dlp.cookies import YoutubeDLCookieJar
from yt_dlp.networking.common import RequestDirector
from yt_dlp.networking.impersonate import ImpersonateTarget
from yt_dlp.YoutubeDL import YoutubeDL

from remora._ydl.types import YDLParams
from remora.path import get_cache_dir

__all__ = ["YDL", "YDLNetworkContext"]

if TYPE_CHECKING:
    from remora.models.options import NetworkOptions


class _LoguruYDLWrapper:
    """Intercepts yt-dlp logs and routes them to Loguru strictly in DEBUG mode."""

    EXCLUDED_LOGS = ("ffmpeg not found.",)

    def __init__(self) -> None:
        self.logger = logger.patch(lambda record: record.update(name="yt-dlp"))

    def debug(self, msg: str):
        if self.exclude(msg):
            return
        self.logger.debug(msg)

    def warning(self, msg: str):
        if self.exclude(msg):
            return
        self.logger.warning(msg)

    def error(self, msg: str):
        if self.exclude(msg):
            return
        self.logger.error(msg)

    def exclude(self, msg: str) -> bool:
        for excluded in self.EXCLUDED_LOGS:
            if msg.startswith(excluded):
                return True
        return False


@dataclass(slots=True)
class YDLNetworkContext(ContextManagerMixin):
    request_director: RequestDirector
    cookiejar: YoutubeDLCookieJar
    proxies: dict[str, Any]
    close_hooks: list[Callable[[], None]]

    @classmethod
    def from_options(cls, options: NetworkOptions) -> Self:
        ydl = YoutubeDL(
            {
                "cookiefile": StringIO(cookies.to_netscape_cookies())
                if (cookies := options.cookies)
                else None,
                "proxy": str(proxy) if (proxy := options.proxy) else None,
                "impersonate": ImpersonateTarget.from_str(impersonate)
                if (impersonate := options.impersonate)
                else None,
            },
            auto_init=False,
        )
        return cls.from_ydl(ydl)

    @classmethod
    def from_ydl(cls, ydl: YoutubeDL) -> Self:
        return cls(
            request_director=ydl._request_director,
            cookiejar=ydl.cookiejar,
            proxies=ydl.proxies,
            close_hooks=ydl._close_hooks,
        )

    @classmethod
    def create(cls) -> Self:
        return cls.from_ydl(YoutubeDL(auto_init=False))

    def close(self) -> None:
        self.request_director.close()

        for close_hook in self.close_hooks:
            close_hook()

    @override
    @contextmanager
    def __contextmanager__(self) -> Generator[Self, None]:
        try:
            yield self
        finally:
            self.close()


class YDLContext(ContextManagerMixin, ABC):
    def __init__(self, context: YDLNetworkContext | None = None):
        self.context = context or YDLNetworkContext.create()

    @override
    @contextmanager
    def __contextmanager__(self) -> Generator[Self, None]:
        with self.context:
            yield self


class YDL(YoutubeDL):
    """Custom `YoutubeDL` class."""

    def __init__(
        self,
        params: YDLParams | None = None,
        network_context: YDLNetworkContext | None = None,
        auto_init: bool = False,
    ):
        self.network_context = network_context or YDLNetworkContext.create()

        # Default parameters
        opts: YDLParams = {
            # Adapt logs
            "logger": _LoguruYDLWrapper(),
            "no_warnings": False,
            "verbose": False,
            # Remove side-effects
            "ignoreerrors": False,
            "consoletitle": False,
            "noprogress": True,
            "quiet": True,
            # Disable Colors
            "color": {"stdout": "no_color", "stderr": "no_color"},
            # Set cache dir relative to library
            "cachedir": get_cache_dir() / "ydl",
            # Remove FFmpeg detection for consistent results
            # If yt-dlp found a inexistent path, it'll disable FFmpeg
            "ffmpeg_location": tempfile.gettempdir(),
        }

        # Custom parameters
        opts |= params or {}

        # Initialize
        super().__init__(
            opts,  # type: ignore
            auto_init,
        )

    @override
    @cached_property
    def proxies(self) -> dict:
        return self.network_context.proxies

    @override
    @cached_property
    def cookiejar(self) -> YoutubeDLCookieJar:
        return self.network_context.cookiejar

    @override
    @cached_property
    def _request_director(self) -> RequestDirector:
        return self.network_context.request_director
