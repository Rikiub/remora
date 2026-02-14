from typing import Annotated, Literal
from pydantic import BeforeValidator, Field, OnErrorOmit, RootModel
from remora.models.base import YDLSerializable
from remora.models.metadata.base import Metadata


class BaseSubtitle(Metadata, YDLSerializable):
    extension: Annotated[str, Field(alias="ext")]


class SubtitleData(BaseSubtitle):
    data: str
    type: Literal["data"] = "data"


class SubtitleUrl(BaseSubtitle):
    name: Annotated[str, Field(alias="name")] = ""
    url: str
    type: Literal["url"] = "url"


def _set_type(v: dict) -> dict:
    if isinstance(v, dict):
        if "data" in v:
            v["type"] = "data"
        elif "url" in v:
            v["type"] = "url"
    return v


Subtitle = Annotated[
    SubtitleUrl | SubtitleData,
    BeforeValidator(_set_type),
    Field(discriminator="type"),
]


class Subtitles(
    YDLSerializable,
    RootModel[
        dict[
            str,
            list[OnErrorOmit[Subtitle]],
        ]
    ],
):
    @property
    def languages(self) -> list[str]:
        return list(self.root.keys())

    def __getitem__(self, key: str) -> list[Subtitle]:
        return self.root[key]

    def __bool__(self) -> bool:
        return bool(self.root)
