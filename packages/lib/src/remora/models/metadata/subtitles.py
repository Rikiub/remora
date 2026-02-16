from __future__ import annotations

from typing import Annotated, Generic, Literal, Self, overload

from pydantic import BeforeValidator, Field
from typing_extensions import TypeVar

from remora.models.base import BaseList, YDLSerializable
from remora.models.metadata.base import Metadata

SubtitleType = Literal["remote", "content"]


class BaseSubtitle(Metadata, YDLSerializable):
    type: SubtitleType
    language: str
    name: str = ""
    extension: Annotated[str, Field(alias="ext")]


class SubtitleRemote(BaseSubtitle):
    type: Literal["remote"] = "remote"  # type: ignore
    url: str


class SubtitleContent(BaseSubtitle):
    type: Literal["content"] = "content"  # type: ignore
    content: Annotated[str, Field(alias="data")]


def _parse_ydl_subtitles(data):
    if isinstance(data, dict):
        subtitles: dict[str, list[dict[str, str]]] = data
        flat_subtitles = []

        for lang, sub in subtitles.items():
            for value in sub:
                sub_type: SubtitleType = "remote" if "url" in value else "content"
                entry = {
                    **value,
                    "type": sub_type,
                    "content": value.get("data"),
                    "language": lang,
                }
                flat_subtitles.append(entry)

        return flat_subtitles
    return data


Subtitle = Annotated[
    SubtitleRemote | SubtitleContent,
    Field(discriminator="type"),
]

T = TypeVar("T", bound=BaseSubtitle, default=BaseSubtitle)


class SubtitleList(YDLSerializable, BaseList[Subtitle], Generic[T]):
    root: Annotated[
        list[Subtitle],
        BeforeValidator(_parse_ydl_subtitles),
    ] = []

    @property
    def languages(self) -> set[str]:
        """Return all unique language codes available."""
        return {s.language for s in self.root if s.type == "remote"}

    def filter(self, language: str | None = None, extension: str | None = None) -> Self:
        """Filter subtitles by options."""

        items = (s for s in self.root)

        if language:
            items = (
                s
                for s in items
                if isinstance(s, SubtitleRemote) and s.language.startswith(language)
            )
        if extension:
            items = (s for s in items if s.extension == extension)

        return self.__class__(list(items))

    @overload
    def by_type(self, type: Literal["remote"]) -> SubtitleList[SubtitleRemote]: ...

    @overload
    def by_type(self, type: Literal["content"]) -> SubtitleList[SubtitleContent]: ...

    def by_type(
        self, type: SubtitleType
    ) -> SubtitleList[SubtitleRemote] | SubtitleList[SubtitleContent]:
        if type == "remote":
            model = SubtitleRemote
        elif type == "content":
            model = SubtitleContent
        else:
            raise ValueError("Invalid subtitle type:", type)

        return SubtitleList[model](  # type: ignore
            [item for item in self if item.type == type],
        )

    def to_ydl_dict(self):
        """Convert back into the nested yt-dlp dictionary format:"""

        data: dict[str, list[dict[str, str]]] = {}

        for sub in self.root:
            entry = sub.model_dump(
                by_alias=True,
                exclude={"type", "language"},
            )
            data[sub.language] = [entry]

        return data
