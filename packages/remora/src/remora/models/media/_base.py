from typing import Annotated

from pydantic import AfterValidator, AliasChoices, AnyUrl, Field, model_validator
from typing_extensions import TypeIs, override

from remora.models._base import EnsureNone, EnsureTuple, RemoraModel, YDLSerializable
from remora.models.metadata import (
    Channel,
    DateMetadata,
    Metrics,
    Thumbnails,
    Uploader,
)

# Types
URL_CHOICES = ("webpage_url", "original_url", "url")


def is_ydl_media(data) -> TypeIs[dict]:
    return isinstance(data, dict) and bool(
        data.get("extractor_key") or data.get("ie_key")
    )


def get_ydl_extractor_key(data: dict) -> str | None:
    return data.get("extractor_key") or data.get("ie_key")


# Base
class ExtractorInfo(RemoraModel):
    id: str
    name: str


class BaseExtract(YDLSerializable):
    extractor: ExtractorInfo

    @override
    def _to_ydl_dict(self) -> dict:
        info = super()._to_ydl_dict()
        info |= info["extractor"]
        return info

    @model_validator(mode="before")
    @classmethod
    def _validate_ydl_extractor(cls, data) -> dict:
        if is_ydl_media(data):
            extractor = data.get("extractor", None)
            if isinstance(extractor, dict):
                extractor = extractor.get("name")

            data["extractor"] = {
                "id": get_ydl_extractor_key(data),
                "name": extractor,
            }
        return data


class ExtractData(BaseExtract):
    """Base identifier for media objects."""

    # Identifier
    id: str
    url: Annotated[AnyUrl, Field(validation_alias=AliasChoices(*URL_CHOICES))]

    # Author
    uploader: Annotated[Uploader | None, EnsureNone] = None
    channel: Annotated[Channel | None, EnsureNone] = None

    # Contributors
    creators: Annotated[tuple[str, ...], EnsureTuple] = ()
    cast: Annotated[tuple[str, ...], EnsureTuple] = ()

    # Metadata
    date: DateMetadata = DateMetadata()
    metrics: Metrics = Metrics()
    thumbnails: Annotated[
        Thumbnails,
        AfterValidator(lambda c: c.sorted_by("best")),
    ] = Thumbnails()

    @property
    def _is_audio_only(self) -> bool:
        """Determine if the media only provides audio (like music or podcasts sites).

        This uses a very fixed list and shouldn't be used as source of truth for everything.
        """
        return self.url.host in ("music.youtube.com", "soundcloud.com")

    @override
    def _to_ydl_dict(self):
        data = super()._to_ydl_dict()

        fields = [
            "date",
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
            data["date"] = data

            if (uploader := data.get("uploader", None)) and isinstance(uploader, str):
                data["uploader"] = {**data, "uploader": uploader}

            if (channel := data.get("channel", None)) and isinstance(channel, str):
                data["channel"] = {**data, "channel": channel}

            return data
        return data
