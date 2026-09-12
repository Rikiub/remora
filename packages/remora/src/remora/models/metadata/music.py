from collections.abc import Sequence
from typing import Annotated

from pydantic import BeforeValidator, Field

from remora.models._base import EnsureTuple, YDLSerializable
from remora.models.metadata._base import Metadata

__all__ = ["MusicMetadata"]


def _normalize_artists(value: str | Sequence[str]) -> tuple[str, ...]:
    artists = []

    # Split separated artists by comma
    if isinstance(value, str) and (values := value.split(",")):
        artists = values

    if len(artists) == 1 and (values := artists[0].split(",")):
        artists = values

    # Remove duplicates
    artists = tuple(v.strip() for v in artists)
    artists = tuple(dict.fromkeys(artists))

    return artists


_ValidateArtists = BeforeValidator(_normalize_artists)


class MusicMetadata(Metadata, YDLSerializable):
    title: Annotated[str | None, Field(alias="track")] = None
    artists: Annotated[
        tuple[str, ...],
        EnsureTuple,
        _ValidateArtists,
        Field(alias="artist"),
    ] = ()
    album: str | None = None
    album_artists: Annotated[
        tuple[str, ...],
        EnsureTuple,
        _ValidateArtists,
        Field(alias="album_artist"),
    ] = ()
    year: Annotated[int | None, Field(alias="release_year")] = None
    genres: tuple[str, ...] = ()
