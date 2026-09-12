from typing import Annotated

from pydantic import AfterValidator, AnyUrl

from remora.models._base import RemoraModel
from remora.models.cookies import Cookies
from remora.models.impersonate import ImpersonateClient, validate_impersonate_target

__all__ = ["NetworkOptions"]


class NetworkOptions(RemoraModel):
    proxy: AnyUrl | None = None
    cookies: Cookies | None = None
    impersonate: Annotated[
        ImpersonateClient | str | None,
        AfterValidator(lambda v: validate_impersonate_target(v) if v else None),
    ] = None
