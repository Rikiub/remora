from typing import Annotated

from pydantic import Field, computed_field

from remora.models.metadata._base import Metadata

__all__ = ["Chapter", "Heatmap", "Segment"]


class Segment(Metadata):
    start: Annotated[float, Field(alias="start_time")]
    end: Annotated[float, Field(alias="end_time")]

    @computed_field
    @property
    def duration(self) -> float:
        return self.end - self.start


class Chapter(Segment):
    title: str


class Heatmap(Segment):
    intensity: Annotated[float, Field(alias="value")]
