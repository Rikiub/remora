from typing import Annotated

from pydantic import BeforeValidator, Field

from remora.models._base import EnsureList, YDLSerializable
from remora.models.metadata._base import Metadata


def _normalize_artists(value: str | list[str]) -> list[str]:
    artists = []

    # Split separated artists by comma
    if isinstance(value, str) and (values := value.split(",")):
        artists = values

    if len(artists) == 1 and (values := artists[0].split(",")):
        artists = values

    # Remove duplicates
    artists = [v.strip() for v in artists]
    artists = list(dict.fromkeys(artists))

    return artists


ValidateArtists = BeforeValidator(_normalize_artists)


class MusicMetadata(Metadata, YDLSerializable):
    track: str | None = None
    artists: Annotated[
        list[str],
        EnsureList,
        ValidateArtists,
        Field(alias="artist"),
    ] = []  # noqa: RUF012
    album: str | None = None
    album_artists: Annotated[
        list[str],
        EnsureList,
        ValidateArtists,
        Field(alias="album_artist"),
    ] = []  # noqa: RUF012
    genres: list[str] = []  # noqa: RUF012
