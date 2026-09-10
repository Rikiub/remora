from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

from remora._ydl.base import YDL

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
