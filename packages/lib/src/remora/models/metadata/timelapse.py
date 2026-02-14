from remora.models.base import YDLSerializable
from remora.models.metadata.base import Metadata


class Timelapse(Metadata):
    start_time: float
    end_time: float


class Chapter(Timelapse, YDLSerializable):
    start_time: float
    end_time: float
    title: str


class Heatmap(Timelapse):
    value: float
