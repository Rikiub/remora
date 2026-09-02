from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BeforeValidator,
    Field,
    field_validator,
    model_validator,
)

from remora.models._base import EnsureList, EnsureNone
from remora.models.media._base import (
    PLAYLIST_EXTRACTOR_IDS,
    ExtractID,
    Extractor,
    TypeField,
    is_ydl_media,
)
from remora.models.metadata import (
    Chapter,
    Heatmap,
    MusicMetadata,
    StoryboardList,
    SubtitleList,
    ThumbnailList,
)
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
    title: Annotated[str | None, EnsureNone] = None
    description: Annotated[str | None, EnsureNone] = None
    live_status: LiveStatus = "not_live"

    # Metadata
    duration: float | None = None
    heatmap: Annotated[list[Heatmap], EnsureList] = []  # noqa: RUF012
    music: Annotated[MusicMetadata | None, EnsureNone] = None

    categories: Annotated[list[str], EnsureList] = []  # noqa: RUF012
    tags: Annotated[list[str], EnsureList] = []  # noqa: RUF012

    thumbnails: Annotated[
        ThumbnailList,
        AfterValidator(lambda list: list.sorted_by("best")),
    ] = ThumbnailList()

    @field_validator("extractor")
    @classmethod
    def _validate_extractor(cls, extractor: Extractor) -> Extractor:
        if extractor.id in PLAYLIST_EXTRACTOR_IDS:
            raise ValueError(f"'{extractor.id}' extractor is for playlists only.")
        return extractor

    @model_validator(mode="before")
    @classmethod
    def _validate_ydl_media(cls, data) -> dict:
        if is_ydl_media(data):
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

            # Map subtitles
            data["subtitles"] = SubtitleList._from_ydl_dict(data)

            # Map storyboards
            data["storyboards"] = StoryboardList._from_ydl_formats(
                data.get("formats") or []
            )

            # Return normalized data
            return data
        return data


class Media(LazyMedia):
    """Online media representation."""

    subtitles: SubtitleList = SubtitleList()
    chapters: Annotated[list[Chapter], EnsureList] = []  # noqa: RUF012
    storyboards: Annotated[
        StoryboardList,
        AfterValidator(lambda list: list.sorted_by("best")),
    ] = StoryboardList()
    streams: Annotated[
        StreamList,
        AfterValidator(lambda list: list.sorted_by("best")),
        Field(alias="formats"),
    ] = StreamList()
