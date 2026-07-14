from __future__ import annotations

from abc import ABC
from typing import Annotated, Literal

from pydantic import (
    AliasChoices,
    Field,
    HttpUrl,
    SkipValidation,
    computed_field,
)

from remora.models.media._base import (
    URL_CHOICES,
    BaseExtract,
    ExtractID,
    ExtractorField,
    TypeField,
)
from remora.models.media.item import LazyMedia
from remora.models.metadata.thumbnail import Thumbnail


class MediaList(ABC, BaseExtract):
    entries: Annotated[
        list[LazyMedia | LazyPlaylist], Field(alias="entries", repr=False)
    ] = []
    extractor: ExtractorField

    @computed_field
    @property
    def medias(self) -> list[LazyMedia]:
        return [item for item in self.entries if item.type == "media"]

    @computed_field
    @property
    def playlists(self) -> list[LazyPlaylist]:
        return [item for item in self.entries if item.type == "playlist"]


class LazyPlaylist(MediaList, ExtractID):
    type: Annotated[Literal["playlist"], SkipValidation] = "playlist"

    url: Annotated[
        HttpUrl,
        Field(
            alias="playlist_url",
            validation_alias=AliasChoices("playlist_url", *URL_CHOICES),
        ),
    ]
    id: Annotated[
        str,
        Field(
            alias="playlist_id",
            validation_alias=AliasChoices("playlist_id", "id"),
        ),
    ]
    title: Annotated[
        str,
        Field(
            alias="playlist_title",
            validation_alias=AliasChoices("playlist_title", "title"),
        ),
    ] = ""

    thumbnails: list[Thumbnail] = []


class Playlist(LazyPlaylist):
    type: Annotated[Literal["playlist"], TypeField] = "playlist"


class SearchList(MediaList):
    type: Literal["search"] = "search"

    service: str
    query: str
