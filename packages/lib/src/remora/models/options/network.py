from pydantic import HttpUrl

from remora.models import CookieList
from remora.models._base import RemoraModel

__all__ = ["NetworkOptions"]


class NetworkOptions(RemoraModel):
    proxy: HttpUrl | None = None
    cookies: CookieList | None = None
    impersonate: str | None = None
