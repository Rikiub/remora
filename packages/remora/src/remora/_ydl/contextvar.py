from abc import ABC
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Self

from anyio import ContextManagerMixin

from remora._ydl.wrapper import YDL
from remora.models.options import NetworkOptions

__all__ = ["YDL", "YDLContext", "get_ydl_session"]

_YDL_SESSION: ContextVar[YDL | None] = ContextVar("ydl_session", default=None)


@contextmanager
def get_ydl_session() -> Generator[YDL]:
    if ydl := _YDL_SESSION.get():
        yield ydl
    else:
        ydl = YDL()
        token = _YDL_SESSION.set(ydl)

        try:
            with ydl:
                yield ydl
        finally:
            _YDL_SESSION.reset(token)


class YDLContext(ContextManagerMixin, ABC):
    def __init__(self, network_options: NetworkOptions | None = None):
        self.network_options = network_options or NetworkOptions()

    @contextmanager
    def __contextmanager__(self) -> Generator[Self, None]:
        with get_ydl_session() as ydl:
            self._ydl_session = ydl
            self._setup()
            yield self

    def _setup(self): ...
