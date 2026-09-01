from typing import Generic, Literal, Self, TypeVar

from pydantic import AnyUrl

from remora.models._base import BaseList, RemoraModel, YDLSerializable
from remora.models.metadata import Resolution
from remora.models.protocol import Protocol


class StoryboardFragment(RemoraModel):
    url: AnyUrl
    duration: float


class Storyboard(RemoraModel):
    id: str
    extension: str
    protocol: Protocol = Protocol.MHTML
    resolution: Resolution | None = None
    fps: float | None = None
    rows: int | None = None
    columns: int | None = None
    fragments: list[StoryboardFragment]

    @classmethod
    def _from_ydl_format_dict(cls, info: dict) -> Self:
        info["id"] = info.get("format_id")
        info["extension"] = info.get("ext")

        if info.get("width") and info.get("height"):
            info["resolution"] = Resolution._from_ydl_dict(info)

        return cls(**info)


_T = TypeVar("_T", bound=Storyboard)


class StoryboardList(YDLSerializable, BaseList[_T], Generic[_T]):
    def filter(self, width: int, height: int) -> Self:
        """Filter storyboards by options."""

        items = self.root

        if width:
            items = (
                s for s in self.root if s.resolution and s.resolution.width == width
            )
        if height:
            items = (
                s for s in self.root if s.resolution and s.resolution.height == height
            )

        return self.__class__(list(items))

    def sorted_by(
        self,
        attribute: Literal["best", "width", "height"],
        reverse: bool = True,
    ) -> Self:
        """Sort by `Storyboard` attribute."""

        if attribute == "best":
            filter = self._sort_by_best_filter
        else:
            filter = lambda s: getattr(s, attribute)

        return self.__class__(
            sorted(
                self.root,
                key=filter,
                reverse=reverse,
            )
        )

    def _sort_by_best_filter(self, storyboard: _T) -> tuple[int, ...]:
        return (
            storyboard.resolution.width if storyboard.resolution else -1,
            storyboard.resolution.height if storyboard.resolution else -1,
        )

    @classmethod
    def _from_ydl_formats(cls, formats: list[dict]) -> Self:
        entries = []

        for entry in formats:
            if entry.get("format_note") == "storyboard":
                entries.append(Storyboard._from_ydl_format_dict(entry))

        return cls(entries)
