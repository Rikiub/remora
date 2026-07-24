from typing import Generic, Literal, Self, TypeVar

from pydantic import model_validator
from typing_extensions import override

from remora.models._base import BaseList, Resolution, YDLSerializable
from remora.models.metadata._base import Metadata


class Thumbnail(Metadata, YDLSerializable):
    id: str = ""
    url: str
    resolution: Resolution | None = None

    @override
    def to_ydl_dict(self):
        data = super().to_ydl_dict()

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

            return data
        return data


T = TypeVar("T")


class ThumbnailList(YDLSerializable, BaseList[T], Generic[T]):
    def filter(self, width: int, height: int) -> Self:
        """Filter thumbnails by options."""

        items = (s for s in self.root)
        return self.__class__(list(items))

    def sorted_by(
        self,
        attribute: Literal["best"],
        reverse: bool = True,
    ) -> Self:
        """Sort by `Thumbnail` attribute."""

        filter = lambda s: getattr(s, attribute)  # noqa: E731

        return self.__class__(
            sorted(
                self.root,
                key=filter,
                reverse=reverse,
            )
        )
