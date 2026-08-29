from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, field_serializer

from remora.models._base import BaseList, EnsureNone

__all__ = ["Cookie", "CookieList"]


class Cookie(BaseModel):
    name: str
    value: str
    domain: str
    path: str = "/"
    expires: Annotated[datetime | None, EnsureNone] = None

    @field_serializer("expires")
    def _serialize_expires_to_timestamp(self, dt: datetime | None) -> float | None:
        return dt.timestamp() if dt else None


class CookieList(BaseList[Cookie]):
    @classmethod
    def from_http_cookies(cls, data: str) -> Self:
        from remora._ydl.cookies import LenientSimpleCookie

        parsed = LenientSimpleCookie(data)
        return cls(
            Cookie(
                name=name,
                value=morsel.value,
                domain=morsel["domain"],
                path=morsel["path"],
                expires=morsel["expires"],
            )
            for name, morsel in parsed.items()
        )

    def to_http_cookies(self) -> str:
        from remora._ydl.cookies import LenientSimpleCookie

        encoder = LenientSimpleCookie()
        values = []

        for c in self:
            _, encoded_value = encoder.value_encode(c.value)

            values.append(f"{c.name}={encoded_value}")
            values.append(f"Domain={c.domain}")
            values.append(f"Path={c.path}")
            values.append(f"Expires={c.expires}")
        return "; ".join(values)
