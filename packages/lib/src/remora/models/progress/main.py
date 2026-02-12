from typing import Annotated

from pydantic import Field
from remora.models.progress.list import PlaylistEvent
from remora.models.progress.media import MediaEvent


DownloadEvent = Annotated[
    PlaylistEvent | MediaEvent,
    Field(discriminator="type"),
]
