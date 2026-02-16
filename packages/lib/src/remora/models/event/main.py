from typing import Annotated

from pydantic import Field

from remora.models.event.list import PlaylistEvent
from remora.models.event.media import MediaEvent

DownloadEvent = Annotated[
    PlaylistEvent | MediaEvent,
    Field(discriminator="type"),
]
