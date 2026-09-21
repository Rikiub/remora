from __future__ import annotations

from abc import ABC
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass
from io import StringIO
from typing import TYPE_CHECKING, Any, Self

from anyio import ContextManagerMixin
from typing_extensions import override
from yt_dlp.cookies import YoutubeDLCookieJar
from yt_dlp.networking.common import RequestDirector
from yt_dlp.networking.impersonate import ImpersonateTarget
from yt_dlp.YoutubeDL import YoutubeDL

if TYPE_CHECKING:
    from remora.models.options import NetworkOptions

__all__ = ["YDLNetworkContext"]


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
