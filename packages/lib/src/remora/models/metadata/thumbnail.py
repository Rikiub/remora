from typing import Generic, Literal, Self, TypeVar

from pydantic import model_validator

from remora.models._base import BaseList, Resolution, YDLSerializable
from remora.models.metadata._base import Metadata


class Thumbnail(Metadata, YDLSerializable):
    id: str = ""
    url: str
    resolution: Resolution | None = None

    @model_validator(mode="before")
    @classmethod
    def _validate_ydl_thumbnail(cls, data):
        if isinstance(data, dict):
            resolution = data.get("resolution")
            width = data.get("width")
            height = data.get("height")

            if isinstance(resolution, str) and width and height:
                data["resolution"] = {
                    "width": data["width"],
                    "height": data["height"],
                }
            else:
                data["resolution"] = None

            return data
        return data


T = TypeVar("T")


class ThumbnailList(YDLSerializable, BaseList[T], Generic[T]):
    root: list[T] = []

    def filter(self, width: int, height: int) -> Self:
        """Filter subtitles by options."""

        items = (s for s in self.root)
        return self.__class__(list(items))

    def sort_by(
        self,
        attribute: Literal["best", "extension", "quality", "codec", "protocol"],
        reverse: bool = True,
    ) -> Self:
        """Sort by `Stream` attribute."""

        filter = lambda s: getattr(s, attribute)  # noqa: E731

        return self.__class__(
            sorted(
                self.root,
                key=filter,
                reverse=reverse,
            )
        )
