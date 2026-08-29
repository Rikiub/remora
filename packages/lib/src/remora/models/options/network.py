from pydantic import HttpUrl

from remora.models._base import RemoraModel

__all__ = ["NetworkOptions"]


class NetworkOptions(RemoraModel):
    proxy: HttpUrl | None = None
    cookies: str | None = None
    impersonate: str | None = None
