from datetime import datetime
from typing import Annotated

from pydantic import AliasChoices, Field, HttpUrl, model_validator
from typing_extensions import override

from remora.models._base import EnsureNone, YDLSerializable
from remora.models.metadata.social import Channel, Metrics, Uploader

# Types
PLAYLIST_EXTRACTORS = ["YoutubeTab"]
URL_CHOICES = ["original_url", "url", "webpage_url"]

# Fields
TypeField = Field(alias="_type")
ExtractorField = Annotated[
    str,
    Field(
        alias="extractor_key",
        validation_alias=AliasChoices("extractor_key", "ie_key"),
    ),
]


def is_ydl_media(data) -> bool:
    return isinstance(data, dict) and bool(
        data.get("extractor_key") or data.get("ie_key")
    )


# Base
class BaseExtract(YDLSerializable): ...


class ExtractID(BaseExtract):
    """Base identifier for media objects."""

    id: str
    extractor: ExtractorField
    url: Annotated[HttpUrl, Field(validation_alias=AliasChoices(*URL_CHOICES))]

    modified_date: Annotated[datetime | None, EnsureNone] = None
    upload_date: Annotated[datetime | None, EnsureNone] = None
    release_date: Annotated[datetime | None, EnsureNone] = None

    uploader: Annotated[Uploader | None, EnsureNone] = None
    channel: Annotated[Channel | None, EnsureNone] = None
    metrics: Annotated[Metrics | None, EnsureNone] = None

    @override
    def to_ydl_dict(self):
        data = super().to_ydl_dict()

        fields = [
            "music",
            "metrics",
            "uploader",
            "channel",
        ]
        for f in fields:
            data |= data.get(f) or {}

        return data

    @model_validator(mode="before")
    @classmethod
    def _validate_ydl_base(cls, data) -> dict:
        if is_ydl_media(data):
            data["metrics"] = data

            if (uploader := data.get("uploader", None)) and isinstance(uploader, str):
                data["uploader"] = {**data, "uploader": uploader}

            if (channel := data.get("channel", None)) and isinstance(channel, str):
                data["channel"] = {**data, "channel": channel}

            return data
        return data
