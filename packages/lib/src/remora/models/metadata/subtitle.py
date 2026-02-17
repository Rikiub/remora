from __future__ import annotations

from typing import Annotated, Generic, Literal, Self

from pydantic import BeforeValidator, Field, HttpUrl
from typing_extensions import TypeVar

from remora.models._base import BaseList, YDLSerializable
from remora.models.metadata._base import Metadata

SubtitleType = Literal["external", "embedded"]


class BaseSubtitle(Metadata, YDLSerializable):
    type: SubtitleType
    name: str = ""
    language: str
    extension: Annotated[str, Field(alias="ext")]

    def to_ydl_dict(self) -> dict[str, list[dict[str, str]]]:
        entry = self.model_dump(
            by_alias=True,
            mode="json",
            exclude={"type", "language"},
        )
        data = {self.language: [entry]}
        return data


class ExternalSubtitle(BaseSubtitle):
    type: Literal["external"] = "external"  # type: ignore
    url: HttpUrl


class EmbeddedSubtitle(BaseSubtitle):
    type: Literal["embedded"] = "embedded"  # type: ignore
    text: Annotated[str, Field(alias="data")]


Subtitle = Annotated[
    ExternalSubtitle | EmbeddedSubtitle,
    Field(discriminator="type"),
]


def _parse_ydl_subtitles(data):
    if isinstance(data, dict):
        subtitles: dict[str, list[dict[str, str]]] = data
        flat_subtitles = []

        for lang, sub in subtitles.items():
            for value in sub:
                sub_type: SubtitleType = "external" if "url" in value else "embedded"
                entry = {
                    **value,
                    "type": sub_type,
                    "content": value.get("data"),
                    "language": lang,
                }
                flat_subtitles.append(entry)

        return flat_subtitles
    return data


T = TypeVar("T", bound=Subtitle, default=Subtitle)


class SubtitleList(YDLSerializable, BaseList[T], Generic[T]):
    root: Annotated[
        list[T],
        BeforeValidator(_parse_ydl_subtitles),
    ] = []

    @property
    def languages(self) -> set[str]:
        """Return all unique language codes available."""
        return {s.language for s in self.root if isinstance(s, ExternalSubtitle)}

    @property
    def external(self) -> SubtitleList[ExternalSubtitle]:
        """Subtitles hosted on a URL."""
        return SubtitleList[ExternalSubtitle](  # type: ignore
            [item for item in self if isinstance(item, ExternalSubtitle)],
        )

    @property
    def embedded(self) -> SubtitleList[EmbeddedSubtitle]:
        """Subtitles found inside the media file."""
        return SubtitleList[EmbeddedSubtitle](  # type: ignore
            [item for item in self if isinstance(item, EmbeddedSubtitle)],
        )

    def filter(self, language: str | None = None, extension: str | None = None) -> Self:
        """Filter subtitles by options."""

        items = (s for s in self.root)

        if language:
            items = (
                s
                for s in items
                if isinstance(s, ExternalSubtitle) and s.language.startswith(language)
            )
        if extension:
            items = (s for s in items if s.extension == extension)

        return self.__class__(list(items))

    def to_ydl_dict(self):
        """Convert back into the nested yt-dlp dictionary format:"""

        data = {}

        for subtitle in self.root:
            entry = subtitle.to_ydl_dict()

            for lang, sub in entry.items():
                for value in sub:
                    if not data.get(lang):
                        data[lang] = []
                    data[lang].append(value)

        return data
