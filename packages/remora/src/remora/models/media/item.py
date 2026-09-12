from typing import Annotated, Literal

from pydantic import AfterValidator, BeforeValidator, Field, model_validator

from remora.models._base import EnsureNone, EnsureTuple
from remora.models.media._base import ExtractData, is_ydl_media
from remora.models.metadata import (
    Chapter,
    Heatmap,
    MusicMetadata,
    Storyboards,
    Subtitles,
)
from remora.models.stream.list import Streams

__all__ = [
    "Availability",
    "LazyMedia",
    "LiveStatus",
    "Media",
]


def _normalize_type(value: str, literal: str) -> str:
    if value in ("url", "url_transparent", "video"):
        return literal
    return value


LiveStatus = Literal[
    "live",
    "upcoming",
    "was_live",
    "not_live",
]
Availability = Literal[
    "public",
    "private",
    "unlisted",
    "needs_auth",
    "premium_only",
    "subscriber_only",
]


class LazyMedia(ExtractData):
    # Identity
    type: Annotated[
        Literal["lazy_media"],
        BeforeValidator(lambda v: _normalize_type(v, "lazy_media")),
        Field(alias="_type"),
    ] = "lazy_media"

    title: Annotated[str | None, EnsureNone] = None
    description: Annotated[str | None, EnsureNone] = None

    # Status
    live_status: LiveStatus = "not_live"
    availability: Annotated[
        Availability,
        BeforeValidator(lambda v: v if v else "public"),
    ] = "public"

    # Metadata
    license: str | None = None
    location: str | None = None
    age_limit: int | None = None
    duration: float | None = None
    heatmap: Annotated[tuple[Heatmap, ...], EnsureTuple] = ()
    music: Annotated[MusicMetadata | None, EnsureNone] = None

    categories: Annotated[tuple[str, ...], EnsureTuple] = ()
    tags: Annotated[tuple[str, ...], EnsureTuple] = ()

    @model_validator(mode="before")
    @classmethod
    def _validate_ydl_lazy_media(cls, data) -> dict:
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
            data["music"] = {
                **data,
                "title": data.get("track"),
            }

            # Return normalized data
            return data
        return data


class Media(LazyMedia):
    """Online media representation."""

    type: Annotated[
        Literal["media"],
        BeforeValidator(lambda v: _normalize_type(v, "media")),
        Field(alias="_type"),
    ] = "media"

    subtitles: Annotated[
        Subtitles,
        AfterValidator(lambda c: c.sorted_by("best")),
    ] = Subtitles()
    chapters: Annotated[tuple[Chapter, ...], EnsureTuple] = ()
    storyboards: Annotated[
        Storyboards,
        AfterValidator(lambda c: c.sorted_by("best")),
    ] = Storyboards()
    streams: Annotated[
        Streams,
        AfterValidator(lambda c: c.sorted_by("best")),
        Field(alias="formats"),
    ] = Streams()

    @model_validator(mode="before")
    @classmethod
    def _validate_ydl_full_media(cls, data) -> dict:
        if is_ydl_media(data):
            # Map subtitles
            data["subtitles"] = Subtitles._from_ydl_dict(data)

            # Map storyboards
            data["storyboards"] = Storyboards._from_ydl_formats(
                data.get("formats") or []
            )

            # Return normalized data
            return data
        return data
