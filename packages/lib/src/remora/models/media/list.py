from __future__ import annotations

from abc import ABC
from typing import Annotated, Literal

from pydantic import AliasChoices, Field, HttpUrl, computed_field

from remora.models.media._base import (
    URL_CHOICES,
    BaseExtract,
    ExtractID,
    ExtractorField,
)
from remora.models.media.item import LazyMedia
from remora.models.metadata.thumbnail import Thumbnail


class MediaList(ABC, BaseExtract):
    entries: Annotated[list[LazyMedia | LazyPlaylist], Field(repr=False)] = []
    extractor: ExtractorField

    @computed_field
    @property
    def medias(self) -> list[LazyMedia]:
        return [item for item in self.entries if isinstance(item, LazyMedia)]

    @computed_field
    @property
    def playlists(self) -> list[LazyPlaylist]:
        return [item for item in self.entries if isinstance(item, LazyPlaylist)]


class LazyPlaylist(MediaList, ExtractID):
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
    thumbnails: list[Thumbnail] = []


class Playlist(LazyPlaylist): ...


class SearchList(MediaList):
    type: Literal["search"] = "search"

    service: str
    query: str
