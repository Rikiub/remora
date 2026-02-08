import datetime
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    AliasChoices,
    BeforeValidator,
    Field,
    PlainSerializer,
    PrivateAttr,
    field_validator,
)

from remora.models.content.base import PLAYLIST_EXTRACTORS, LazyExtract, TypeField
from remora.models.content.metadata import (
    Chapter,
    MusicMetadata,
    Subtitles,
    Thumbnail,
)
from remora.models.format.list import FormatList
from remora.types import MUSIC_SITES

DatetimeTimestamp = Annotated[
    datetime.datetime, PlainSerializer(lambda d: d.timestamp())
]


def _validate_type(value: str):
    if value in ("url", "url_transparent", "video"):
        return "media"
    return value


class LazyMedia(MusicMetadata, LazyExtract):
    type: Annotated[
        Literal["media"],
        BeforeValidator(_validate_type),
        PlainSerializer(lambda v: "url"),
        TypeField,
    ] = "media"
    title: str = ""
    uploader: Annotated[
        str,
        AfterValidator(lambda v: v.split(",")[0] if v else ""),
        AfterValidator(lambda v: v.removesuffix(" - Topic") if v else ""),
        Field(validation_alias=AliasChoices("creator", "uploader")),
    ] = ""
    uploader_id: str | None = None
    description: str | None = None
    datetime: Annotated[DatetimeTimestamp | None, Field(alias="timestamp")] = None
    duration: float = 0
    thumbnails: list[Thumbnail] = []

    @property
    def is_music(self) -> bool:
        url = str(self.url)

        if any(s in url for s in MUSIC_SITES):
            return True
        else:
            return False

    @field_validator("extractor")
    @classmethod
    def _validate_extractor(cls, v: str) -> str:
        if v in PLAYLIST_EXTRACTORS:
            raise ValueError(f"'{v}' extractor is for playlists only.")
        return v


class Media(LazyMedia):
    """Online media representation."""

    chapters: list[Chapter] | None = None
    subtitles: Subtitles | None = None
    formats: Annotated[
        FormatList,
        AfterValidator(lambda list: list.sort_by("best")),
        Field(min_length=1),
    ]
    is_cache: Annotated[bool, PrivateAttr()] = False
