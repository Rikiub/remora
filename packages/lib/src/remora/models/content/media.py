from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BeforeValidator,
    Field,
    PlainSerializer,
    PrivateAttr,
    field_validator,
    model_validator,
)
from remora.models.base import EnsureList, EnsureNone
from remora.models.content.base import PLAYLIST_EXTRACTORS, LazyExtract, TypeField
from remora.models.metadata.general import Channel, Datetime, Metrics, Uploader
from remora.models.metadata.music import Music
from remora.models.metadata.subtitles import SubtitleList
from remora.models.metadata.thumbnails import Thumbnail
from remora.models.metadata.timelapse import Chapter, Heatmap
from remora.models.stream.list import StreamList


def _validate_type(value: str):
    if value in ("url", "url_transparent", "video"):
        return "media"
    return value


LiveStatus = Literal["live", "upcoming", "was_live", "not_live"]


class LazyMedia(LazyExtract):
    # Identity
    type: Annotated[
        Literal["media"],
        BeforeValidator(_validate_type),
        PlainSerializer(lambda v: "url"),
        TypeField,
    ] = "media"
    title: str = ""
    description: Annotated[str | None, EnsureNone] = None
    live_status: LiveStatus = "not_live"

    # Ownership
    uploader: Annotated[
        Uploader | None,
        EnsureNone,
        Field(alias="uploader_data"),
    ] = None
    channel: Annotated[
        Channel | None,
        EnsureNone,
        Field(alias="channel_data"),
    ] = None
    music: Annotated[Music | None, EnsureNone] = None

    # Engagement
    categories: Annotated[list[str], EnsureList] = []
    tags: Annotated[list[str], EnsureList] = []

    metrics: Annotated[Metrics | None, EnsureNone] = None
    heatmap: list[Heatmap] | None = None

    # Chronology
    datetime: Datetime
    duration: float = 0
    thumbnails: list[Thumbnail] = []

    @field_validator("extractor")
    @classmethod
    def _validate_extractor(cls, v: str) -> str:
        if v in PLAYLIST_EXTRACTORS:
            raise ValueError(f"'{v}' extractor is for playlists only.")
        return v

    @model_validator(mode="before")
    @classmethod
    def _nest_fields(cls, data):
        if isinstance(data, dict):
            # Prepare nested data
            keys = [
                "uploader_data",
                "channel_data",
                "music",
                "metrics",
                "datetime",
            ]

            for key in keys:
                if key not in data:
                    data[key] = data

            # Prepare live status
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

        return data


class Media(LazyMedia):
    """Online media representation."""

    chapters: Annotated[list[Chapter], EnsureList] = []
    subtitles: SubtitleList = SubtitleList()
    streams: Annotated[
        StreamList,
        AfterValidator(lambda list: list.sort_by("best")),
        Field(alias="formats", min_length=1),
    ]
    is_cache: Annotated[bool, PrivateAttr()] = False
