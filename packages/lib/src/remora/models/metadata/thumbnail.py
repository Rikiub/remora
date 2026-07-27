from typing import Generic, Literal, Self

from pydantic import BaseModel, model_validator
from typing_extensions import TypeVar, override

from remora.models._base import BaseList, YDLSerializable
from remora.models.metadata._base import Metadata
from remora.models.metadata.size import Resolution


class ExtractorMeta(BaseModel):
    preference: int = 0


class Thumbnail(Metadata, YDLSerializable):
    id: str = ""
    url: str
    resolution: Resolution | None = None
    extractor_meta: ExtractorMeta = ExtractorMeta()

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

            if isinstance(resolution, str) or resolution is None:
                width = data.get("width")
                height = data.get("height")

                if width and height:
                    data["resolution"] = {"width": width, "height": height}
                else:
                    data["resolution"] = None

            # Map extras
            if "extractor_meta" not in data:
                data["extractor_meta"] = data

            return data
        return data


_T = TypeVar("_T", default=Thumbnail, bound=Thumbnail)


class ThumbnailList(YDLSerializable, BaseList[_T], Generic[_T]):
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
        attribute: Literal["best", "width", "height"],
        reverse: bool = True,
    ) -> Self:
        """Sort by `Thumbnail` attribute."""

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

    def _sort_by_best_filter(self, thumbnail: _T) -> tuple[int, ...]:
        return (
            thumbnail.extractor_meta.preference,
            thumbnail.resolution.width if thumbnail.resolution else -1,
            thumbnail.resolution.height if thumbnail.resolution else -1,
        )
