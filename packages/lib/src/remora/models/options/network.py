from typing import Annotated

from pydantic import AfterValidator, HttpUrl

from remora.models._base import RemoraModel
from remora.models.cookies import CookieList
from remora.models.impersonate import validate_impersonate_target

__all__ = ["NetworkOptions"]


class NetworkOptions(RemoraModel):
    proxy: HttpUrl | None = None
    cookies: CookieList | None = None
    impersonate: Annotated[
        str | None,
        AfterValidator(lambda v: validate_impersonate_target(v) if v else None),
    ] = None
