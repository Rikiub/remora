from typing import Annotated, Generic, Literal, Self

from pydantic import Field, model_validator
from typing_extensions import TypeVar, override

from remora.models._base import (
    BaseList,
    FilterValue,
    RemoraModel,
    YDLSerializable,
    to_tuple,
)
from remora.models.metadata._base import Metadata
from remora.models.metadata.size import Resolution


class ThumbnailRequestContext(RemoraModel):
    headers: Annotated[dict | None, Field(alias="http_headers")] = None


class Thumbnail(Metadata, YDLSerializable):
    id: str = ""
    url: str
    resolution: Resolution | None = None
    priority: Annotated[int, Field(alias="preference")] = 0
    request_context: ThumbnailRequestContext = ThumbnailRequestContext()

    @override
    def _to_ydl_dict(self):
        data = super()._to_ydl_dict()
        if res := self.resolution:
            data |= res.model_dump()
        return data

    @model_validator(mode="before")
    @classmethod
    def _validate_ydl_thumbnail(cls, data):
        if isinstance(data, dict):
            # Map resolution
            if data.get("width") and data.get("height"):
                data["resolution"] = Resolution._from_ydl_dict(data)

            # Map extras
            if "request_context" not in data:
                data["request_context"] = data

            return data
        return data


_T = TypeVar("_T", default=Thumbnail, bound=Thumbnail)


class ThumbnailList(YDLSerializable, BaseList[_T], Generic[_T]):
    def filter(
        self,
        width: FilterValue[int] = None,
        height: FilterValue[int] = None,
    ) -> Self:
        """Filter thumbnails by options."""

        items = self.root

        if width:
            values = to_tuple(width)
            items = (
                s for s in self.root if s.resolution and s.resolution.width in values
            )
        if height:
            values = to_tuple(height)
            items = (
                s for s in self.root if s.resolution and s.resolution.height in values
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
            thumbnail.priority,
            thumbnail.resolution.width if thumbnail.resolution else -1,
            thumbnail.resolution.height if thumbnail.resolution else -1,
        )
