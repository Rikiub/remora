from typing import Annotated

from pydantic import BeforeValidator
from remora.models.base import YDLSerializable
from remora.models.metadata.base import Metadata


def _validate_artists(value: list[str]) -> list[str]:
    if value and len(value) == 1:
        if artists := value[0].split(","):
            return artists
    return value


class Music(Metadata, YDLSerializable):
    track: str | None = None
    artists: Annotated[list[str] | None, BeforeValidator(_validate_artists)] = None
    album: str | None = None
    album_artists: list[str] | None = None
    genres: list[str] | None = None
