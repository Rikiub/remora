from __future__ import annotations

from abc import ABC
from typing import Annotated, Literal, TypeVar

from pydantic import AliasChoices, Field, HttpUrl

from remora.models._base import BaseList
from remora.models.media._base import (
    URL_CHOICES,
    BaseExtract,
    ExtractID,
    ExtractorField,
)
from remora.models.media.item import LazyMedia
from remora.models.metadata import ThumbnailList

# Entries List
_Entry = TypeVar("_Entry", LazyMedia, "LazyPlaylist")


class EntriesList(BaseList[_Entry]):
    def medias(self) -> EntriesList[LazyMedia]:
        return EntriesList(item for item in self.root if isinstance(item, LazyMedia))

    def playlists(self) -> EntriesList[LazyPlaylist]:
        return EntriesList(item for item in self.root if isinstance(item, LazyPlaylist))


class _BaseList(ABC, BaseExtract):
    entries: Annotated[EntriesList, Field(repr=False, default_factory=EntriesList)]
    extractor: ExtractorField


# Search
class SearchList(_BaseList):
    type: Literal["search"] = "search"

    service: str
    query: str


# Playlist
class LazyPlaylist(_BaseList, ExtractID):
    type: Literal["playlist"] = "playlist"

    id: Annotated[
        str,
        Field(validation_alias=AliasChoices("playlist_id", "id")),
    ]
    url: Annotated[
        HttpUrl,
        Field(validation_alias=AliasChoices("playlist_url", *URL_CHOICES)),
    ]
    title: Annotated[
        str,
        Field(
            alias="playlist_title",
            validation_alias=AliasChoices("playlist_url", "title"),
        ),
    ] = ""
    thumbnails: ThumbnailList = ThumbnailList()


class Playlist(LazyPlaylist): ...
