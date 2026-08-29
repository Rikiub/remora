from http.cookiejar import MozillaCookieJar
from io import StringIO
from pathlib import Path
from typing import Annotated, Self

from pydantic import BaseModel

from remora.models._base import BaseList, EnsureBool, EnsureNone
from remora.models.types import StrPath

__all__ = ["Cookie", "CookieList"]


class Cookie(BaseModel):
    name: str
    value: str
    domain: str
    path: str = "/"
    secure: Annotated[bool, EnsureBool] = False
    expires: Annotated[int | None, EnsureNone] = None


class CookieList(BaseList[Cookie]):
    @classmethod
    def from_file(cls, file_path: StrPath) -> Self:
        file_path = Path(file_path)
        content = file_path.read_text()
        extension = file_path.suffix[1:]

        match extension:
            case "txt":
                return cls.from_netscape_cookies(content)
            case "json":
                return cls.from_json(content)
        raise ValueError("Unable to determine cookies file format")

    @classmethod
    def from_json(cls, data: str | bytes | bytearray) -> Self:
        return cls.model_validate_json(data)

    @classmethod
    def from_netscape_cookies(cls, data: str) -> Self:
        jar = MozillaCookieJar()
        jar._really_load(StringIO(data), "<memory>", False, False)  # ty: ignore[unresolved-attribute]

        return cls(
            Cookie(
                name=cookie.name,
                value=cookie.value or "",
                domain=cookie.domain,
                path=cookie.path,
                secure=cookie.secure,
                expires=cookie.expires,
            )
            for cookie in jar
        )

    def to_netscape_cookies(self) -> str:
        lines = [
            "# Netscape HTTP Cookie File",
            "# https://curl.se/rfc/cookie_spec.html",
            "# This is a generated file!  Do not edit.",
            "",
        ]

        for cookie in self:
            domain = cookie.domain
            include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
            path = cookie.path
            secure = "TRUE" if cookie.secure else "FALSE"
            expires = str(cookie.expires if cookie.expires else "0")

            lines.append(
                f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{expires}\t{cookie.name}\t{cookie.value}"
            )

        return "\n".join(lines) + "\n"

    @classmethod
    def from_cookie_header(cls, data: str) -> Self:
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

    def to_cookie_header(self) -> str:
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
