from __future__ import annotations

import re
from abc import ABC
from typing import Annotated, Literal

from pydantic import AliasChoices, AnyUrl, Discriminator, Field, Tag
from typing_extensions import TypeVar

from remora.models._base import BaseTuple
from remora.models.media import Media
from remora.models.media._base import (
    URL_CHOICES,
    BaseExtract,
    ExtractData,
    get_ydl_extractor_key,
    is_ydl_media,
)
from remora.models.media.item import LazyMedia

__all__ = [
    "Entries",
    "LazyPlaylist",
    "Playlist",
    "Search",
]

# Discriminator
_PLAYLIST_EXTRACTOR_RE = re.compile(
    "Tab|Notification|Search|Playlist|Channel|User|Category|Collection"
)


def _infer_extract_type(data) -> str:
    if is_ydl_media(data):
        extractor_key = get_ydl_extractor_key(data) or ""

        # Match playlist
        if data.get("_type") == "playlist" or data.get("entries"):
            return "playlist"

        if _PLAYLIST_EXTRACTOR_RE.search(extractor_key):
            return "lazy_playlist"

        # Match media
        if data.get("formats"):
            return "media"

        return "lazy_media"
    elif isinstance(data, (LazyMedia, LazyPlaylist)):
        return data.type
    raise ValueError("Unable to determine data type")


_ExtractDiscriminator = Annotated[
    Annotated[LazyMedia, Tag("lazy_media")]
    | Annotated[Media, Tag("media")]
    | Annotated["LazyPlaylist", Tag("lazy_playlist")]
    | Annotated["Playlist", Tag("playlist")],
    Discriminator(_infer_extract_type),
]
_Entry = TypeVar("_Entry", bound=_ExtractDiscriminator, default=_ExtractDiscriminator)


# Entries
class Entries(BaseTuple[_Entry]):
    def medias(self) -> Entries[LazyMedia]:
        return Entries(item for item in self.root if isinstance(item, LazyMedia))

    def playlists(self) -> Entries[LazyPlaylist]:
        return Entries(item for item in self.root if isinstance(item, LazyPlaylist))


class _BaseEntries(ABC, BaseExtract):
    entries: Annotated[Entries, Field(repr=False, default_factory=Entries)]


# Search
class Search(_BaseEntries):
    type: Literal["search"] = "search"
    service: str
    query: str


# Playlist
class LazyPlaylist(_BaseEntries, ExtractData):
    type: Literal["lazy_playlist"] = "lazy_playlist"

    id: Annotated[str, Field(alias="playlist_id")]
    url: Annotated[
        AnyUrl,
        Field(validation_alias=AliasChoices("playlist_url", *URL_CHOICES)),
    ]
    title: Annotated[str, Field(alias="playlist_title")] = ""


class Playlist(LazyPlaylist):
    type: Literal["playlist"] = "playlist"
