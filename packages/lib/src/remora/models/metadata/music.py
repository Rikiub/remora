from typing import Annotated

from pydantic import BeforeValidator

from remora.models._base import EnsureList, YDLSerializable
from remora.models.metadata._base import Metadata


def _validate_artists(value: str | list[str]) -> list[str]:
    if isinstance(value, str) and (artists := value.split(",")):
        return artists
    elif isinstance(value, list) and len(value) == 1:
        if artists := value[0].split(","):
            return artists
        else:
            return value
    else:
        raise ValueError(f"{type(value)} must be a list or string")


ValidateArtists = BeforeValidator(_validate_artists)


class MusicMetadata(Metadata, YDLSerializable):
    track: str | None = None
    artists: Annotated[list[str], EnsureList, ValidateArtists] = []
    album: str | None = None
    album_artists: Annotated[list[str], EnsureList, ValidateArtists] = []
    genres: list[str] = []
