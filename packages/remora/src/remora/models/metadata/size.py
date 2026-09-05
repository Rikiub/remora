from typing import Self

from remora.models._base import RemoraModel

__all__ = ["Resolution"]


class Resolution(RemoraModel):
    width: int
    height: int

    @classmethod
    def _from_ydl_dict(cls, data: dict) -> Self:
        width = data.get("width")
        height = data.get("height")

        if width and height:
            return cls(width=width, height=height)
        else:
            raise ValueError("Width and height are required to make the resolution")
