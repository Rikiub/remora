from datetime import datetime
from typing import Annotated

from pydantic import Field

from remora.models.metadata._base import Metadata


class Timestamp(Metadata):
    modified: Annotated[datetime | None, Field(alias="modified_date")] = None
    uploaded: Annotated[datetime | None, Field(alias="upload_date")] = None
    released: Annotated[datetime | None, Field(alias="release_date")] = None
