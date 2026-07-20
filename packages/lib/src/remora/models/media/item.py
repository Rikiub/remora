from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BeforeValidator,
    Field,
    field_validator,
    model_validator,
)
from typing_extensions import override

from remora.models._base import EnsureList, EnsureNone
from remora.models.media._base import PLAYLIST_EXTRACTORS, ExtractID, TypeField
from remora.models.metadata.music import MusicMetadata
from remora.models.metadata.playback import Chapter, Heatmap
from remora.models.metadata.subtitle import SubtitleList
from remora.models.metadata.thumbnail import Thumbnail
from remora.models.stream.list import StreamList


def _normalize_type(value: str):
    if value in ("url", "url_transparent", "video"):
        return "media"
    return value


LiveStatus = Literal["live", "upcoming", "was_live", "not_live"]


class LazyMedia(ExtractID):
    # Identity
    type: Annotated[
        Literal["media"],
        BeforeValidator(_normalize_type),
        TypeField,
    ] = "media"
    type: Literal["media"] = "media"
    title: Annotated[str | None, EnsureNone] = None
    description: Annotated[str | None, EnsureNone] = None
    live_status: LiveStatus = "not_live"

    # Metadata
    duration: float | None = None
    heatmap: Annotated[list[Heatmap], EnsureList] = []
    music: Annotated[MusicMetadata | None, EnsureNone] = None

    categories: Annotated[list[str], EnsureList] = []
    tags: Annotated[list[str], EnsureList] = []

    thumbnails: list[Thumbnail] = []

    @field_validator("extractor")
    @classmethod
    def _validate_extractor(cls, v: str) -> str:
        if v in PLAYLIST_EXTRACTORS:
            raise ValueError(f"'{v}' extractor is for playlists only.")
        return v

    @model_validator(mode="before")
    @classmethod
    @override
    def _validate_ydl_media(cls, data) -> dict:
        if isinstance(data, dict):
            # Map live status
            live_status: LiveStatus = "not_live"

            is_live = data.get("is_live")
            was_live = data.get("was_live")
            is_upcoming = (
                data.get("live_status") == "is_upcoming"
                or data.get("availability") == "upcoming"
            )

            if is_live:
                live_status = "live"
            elif is_upcoming:
                live_status = "upcoming"
            elif was_live:
                live_status = "was_live"

            data["live_status"] = live_status

            # Map metadata
            data["music"] = data

            # Return normalized data
            return data
        return data


class Media(LazyMedia):
    """Online media representation."""

    subtitles: SubtitleList = SubtitleList()
    chapters: Annotated[list[Chapter], EnsureList] = []
    streams: Annotated[
        StreamList,
        AfterValidator(lambda list: list.sort_by("best")),
        Field(alias="formats"),
    ]
