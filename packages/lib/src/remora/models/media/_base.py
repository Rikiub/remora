from datetime import datetime
from typing import Annotated

from pydantic import AliasChoices, Field, HttpUrl, model_validator

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

    @model_validator(mode="before")
    @classmethod
    def _validate_ydl_base(cls, data) -> dict:
        if isinstance(data, dict):
            metrics = data

            if (uploader := data.get("uploader", None)) and isinstance(uploader, str):
                uploader = {**data, "uploader": uploader}

            if (channel := data.get("channel", None)) and isinstance(channel, str):
                channel = {**data, "channel": channel}

            return {
                **data,
                "metrics": metrics,
                "uploader": uploader,
                "channel": channel,
            }
        return data
