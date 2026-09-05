from __future__ import annotations

from abc import ABC
from typing import Annotated, Literal, Union

from pydantic import AliasChoices, AnyUrl, Field
from typing_extensions import TypeVar

from remora.models._base import BaseList
from remora.models.media._base import URL_CHOICES, BaseExtract, ExtractID
from remora.models.media.item import LazyMedia

__all__ = [
    "EntriesList",
    "LazyPlaylist",
    "Playlist",
    "SearchList",
]

# Entries List
_EntryType = Union[LazyMedia, "LazyPlaylist"]
_Entry = TypeVar("_Entry", bound=_EntryType, default=_EntryType)


class EntriesList(BaseList[_Entry]):
    def medias(self) -> EntriesList[LazyMedia]:
        return EntriesList(item for item in self.root if isinstance(item, LazyMedia))

    def playlists(self) -> EntriesList[LazyPlaylist]:
        return EntriesList(item for item in self.root if isinstance(item, LazyPlaylist))


class _BaseList(ABC, BaseExtract):
    entries: Annotated[EntriesList, Field(repr=False, default_factory=EntriesList)]


# Search
class SearchList(_BaseList):
    type: Literal["search"] = "search"
    service: str
    query: str


# Playlist
class LazyPlaylist(_BaseList, ExtractID):
    type: Literal["playlist"] = "playlist"

    id: Annotated[str, Field(alias="playlist_id")]
    url: Annotated[
        AnyUrl,
        Field(validation_alias=AliasChoices("playlist_url", *URL_CHOICES)),
    ]
    title: Annotated[str, Field(alias="playlist_title")] = ""


class Playlist(LazyPlaylist): ...
