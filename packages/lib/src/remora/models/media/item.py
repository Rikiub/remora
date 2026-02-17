from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BeforeValidator,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)

from remora.models._base import EnsureList, EnsureNone
from remora.models.media._base import PLAYLIST_EXTRACTORS, LazyExtract, TypeField
from remora.models.metadata.music import MusicMetadata
from remora.models.metadata.playback import Chapter, Heatmap
from remora.models.metadata.social import Channel, Metrics, Uploader
from remora.models.metadata.subtitle import SubtitleList
from remora.models.metadata.temporal import Timestamp
from remora.models.metadata.thumbnail import Thumbnail
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
        TypeField,
    ] = "media"
    title: str = ""
    description: Annotated[str | None, EnsureNone] = None
    live_status: LiveStatus = "not_live"

    # Temporal
    duration: float = 0
    timestamp: Annotated[Timestamp, Field(alias="timestamp_info")]

    # Social
    uploader: Annotated[
        Uploader | None,
        EnsureNone,
        Field(alias="uploader_info"),
    ] = None
    channel: Annotated[
        Channel | None,
        EnsureNone,
        Field(alias="channel_info"),
    ] = None
    metrics: Annotated[Metrics | None, EnsureNone] = None
    heatmap: list[Heatmap] | None = None

    # Metadata
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
    def _nest_fields(cls, data):
        # Process only in YDL info dicts.
        if isinstance(data, dict) and (data.get("extractor_key") or data.get("ie_key")):
            # Remove conflictive keys
            data.pop("timestamp", None)

            # Prepare nested data
            keys = [
                "uploader_info",
                "channel_info",
                "timestamp_info",
                "metrics",
                "music",
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

    def to_ydl_dict(self):
        info = super().to_ydl_dict()
        info |= {"_type": "url"}
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
