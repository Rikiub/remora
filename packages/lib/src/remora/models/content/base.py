from typing import Annotated

from pydantic import AliasChoices, Field, HttpUrl

from remora.models.base import YDLSerializable

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


# Items
class Extract(YDLSerializable):
    """Base identifier for media objects."""

    extractor: ExtractorField
    url: Annotated[HttpUrl, Field(validation_alias=AliasChoices(*URL_CHOICES))]
    id: str


class LazyExtract(Extract): ...
