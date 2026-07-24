from typing import Generic, Literal, Self

from pydantic import BaseModel, model_validator
from typing_extensions import TypeVar, override

from remora.models._base import BaseList, Resolution, YDLSerializable
from remora.models.metadata._base import Metadata


class ExtractorMeta(BaseModel):
    preference: int


class Thumbnail(Metadata, YDLSerializable):
    id: str = ""
    url: str
    resolution: Resolution | None = None
    extractor_meta: ExtractorMeta

    @override
    def to_ydl_dict(self):
        data = super().to_ydl_dict()
        data |= data.get("extractor_meta", {})

        if res := self.resolution:
            data |= {
                "width": res.width,
                "height": res.height,
            }

        return data

    @model_validator(mode="before")
    @classmethod
    def _validate_ydl_thumbnail(cls, data):
        if isinstance(data, dict):
            # Map resolution
            resolution = data.get("resolution")
            width = data.get("width")
            height = data.get("height")

            if isinstance(resolution, str) and width and height:
                data["resolution"] = {
                    "width": width,
                    "height": height,
                }
            else:
                data["resolution"] = None

            # Map extras
            data["extractor_meta"] = data

            return data
        return data


T = TypeVar("T", bound=Thumbnail)


class ThumbnailList(YDLSerializable, BaseList[T], Generic[T]):
    def filter(self, width: int, height: int) -> Self:
        """Filter thumbnails by options."""

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
        attribute: Literal["best"],
        reverse: bool = True,
    ) -> Self:
        """Sort by `Thumbnail` attribute."""

        if attribute == "best":
            filter = self._sort_by_best_filter
        else:
            filter = lambda s: getattr(s, attribute)  # noqa: E731

        return self.__class__(
            sorted(
                self.root,
                key=filter,
                reverse=reverse,
            )
        )

    def _sort_by_best_filter(self, thumbnail: T) -> tuple[int, ...]:
        return (
            thumbnail.extractor_meta.preference,
            thumbnail.resolution.width if thumbnail.resolution else -1,
            thumbnail.resolution.height if thumbnail.resolution else -1,
        )
