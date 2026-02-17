from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BeforeValidator,
    Field,
    PrivateAttr,
    field_validator,
)
from typing_extensions import override

from remora.models._base import EnsureList, EnsureNone
from remora.models.media._base import PLAYLIST_EXTRACTORS, LazyExtractID, TypeField
from remora.models.metadata.music import MusicMetadata
from remora.models.metadata.playback import Chapter, Heatmap
from remora.models.metadata.subtitle import SubtitleList
from remora.models.metadata.thumbnail import Thumbnail
from remora.models.stream.list import StreamList


def _validate_type(value: str):
    if value in ("url", "url_transparent", "video"):
        return "media"
    return value


LiveStatus = Literal["live", "upcoming", "was_live", "not_live"]


class LazyMedia(LazyExtractID):
    # Identity
    type: Annotated[
        Literal["media"],
        BeforeValidator(_validate_type),
        TypeField,
    ] = "media"
    title: str = ""
    description: Annotated[str | None, EnsureNone] = None
    live_status: LiveStatus = "not_live"

    # Metadata
    duration: float = 0
    heatmap: list[Heatmap] = []
    music: Annotated[MusicMetadata | None, EnsureNone] = None

    categories: Annotated[list[str], EnsureList] = []
    tags: Annotated[list[str], EnsureList] = []

    thumbnails: list[Thumbnail] = []

    def to_ydl_dict(self):
        info = super().to_ydl_dict()
        info |= {"_type": "url"}
        return info

    @field_validator("extractor")
    @classmethod
    def _validate_extractor(cls, v: str) -> str:
        if v in PLAYLIST_EXTRACTORS:
            raise ValueError(f"'{v}' extractor is for playlists only.")
        return v

    @classmethod
    @override
    def _transform_ydl_dict(cls, info):
        info = super()._transform_ydl_dict(info)

        # Nested fields
        info["music"] = info

        # Prepare live status
        live_status: LiveStatus = "not_live"

        is_live = info.get("is_live")
        was_live = info.get("was_live")
        is_upcoming = (
            info.get("live_status") == "is_upcoming"
            or info.get("availability") == "upcoming"
        )

        if is_live:
            live_status = "live"
        elif is_upcoming:
            live_status = "upcoming"
        elif was_live:
            live_status = "was_live"

        info["live_status"] = live_status

        # End
        return info


class Media(LazyMedia):
    """Online media representation."""

    subtitles: SubtitleList = SubtitleList()
    chapters: Annotated[list[Chapter], EnsureList] = []
    streams: Annotated[
        StreamList,
        AfterValidator(lambda list: list.sort_by("best")),
        Field(alias="formats", min_length=1),
    ]
    is_cache: Annotated[bool, PrivateAttr()] = False
