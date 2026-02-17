from remora.models._base import YDLSerializable
from remora.models.metadata._base import Metadata


class Thumbnail(Metadata, YDLSerializable):
    id: str = ""
    url: str
    width: int = 0
    height: int = 0
