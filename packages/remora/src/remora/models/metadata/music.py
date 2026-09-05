from typing import Annotated

from pydantic import BeforeValidator, Field

from remora.models._base import EnsureList, YDLSerializable
from remora.models.metadata._base import Metadata

__all__ = ["MusicMetadata"]


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


_ValidateArtists = BeforeValidator(_normalize_artists)


class MusicMetadata(Metadata, YDLSerializable):
    title: Annotated[str | None, Field(alias="track")] = None
    artists: Annotated[
        list[str],
        EnsureList,
        _ValidateArtists,
        Field(alias="artist"),
    ] = []  # noqa: RUF012
    album: str | None = None
    album_artists: Annotated[
        list[str],
        EnsureList,
        _ValidateArtists,
        Field(alias="album_artist"),
    ] = []  # noqa: RUF012
    year: Annotated[int | None, Field(alias="release_year")] = None
    genres: list[str] = []  # noqa: RUF012
