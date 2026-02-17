from typing import Annotated

from pydantic import BeforeValidator

from remora.models._base import YDLSerializable
from remora.models.metadata._base import Metadata


def _validate_artists(value: list[str]) -> list[str]:
    if len(value) == 1:
        if artists := value[0].split(","):
            return artists
    return value


class MusicMetadata(Metadata, YDLSerializable):
    track: str | None = None
    artists: Annotated[list[str], BeforeValidator(_validate_artists)] = []
    album: str | None = None
    album_artists: list[str] = []
    genres: list[str] = []
