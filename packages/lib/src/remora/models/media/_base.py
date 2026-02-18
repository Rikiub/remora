from typing import Annotated

from pydantic import AliasChoices, Field, HttpUrl, PrivateAttr

from remora._internal.ydl.types import YDLExtractInfo
from remora.models._base import EnsureNone, YDLSerializable
from remora.models.metadata.social import Channel, Metrics, Uploader
from remora.models.metadata.temporal import Timestamp
from remora.models.stream.item import override

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
class BaseExtract(YDLSerializable):
    is_cache: Annotated[bool, PrivateAttr()] = False


class ExtractMetadata(BaseExtract):
    timestamp: Annotated[
        Timestamp,
        Field(alias="timestamp_info"),
    ] = Timestamp()
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
    metrics: Annotated[
        Metrics | None,
        EnsureNone,
    ] = None

    @classmethod
    @override
    def _transform_ydl_dict(cls, info: YDLExtractInfo):
        keys = [
            "timestamp_info",
            "uploader_info",
            "channel_info",
            "metrics",
        ]

        # Prepare nested data
        for key in keys:
            if key not in info:
                info[key] = info

        return info


class ExtractID(ExtractMetadata):
    """Base identifier for media objects."""

    url: Annotated[HttpUrl, Field(validation_alias=AliasChoices(*URL_CHOICES))]
    id: str
    extractor: ExtractorField


class LazyExtractID(ExtractID): ...
