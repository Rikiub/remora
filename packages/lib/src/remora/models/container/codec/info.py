from typing import Generic

from pydantic import computed_field
from typing_extensions import TypeVar

from remora.models._base import RemoraModel
from remora.models.container.codec.audio import AudioCodecFamily
from remora.models.container.codec.video import VideoCodecFamily

_CodecGroup = VideoCodecFamily | AudioCodecFamily
_T = TypeVar("_T", bound=_CodecGroup, default=_CodecGroup)


class CodecInfo(RemoraModel, Generic[_T]):
    original: str

    @computed_field
    @property
    def normalized(self) -> str:
        parts = self.original.split(".")

        if member := (
            VideoCodecFamily.match(parts[0]) or AudioCodecFamily.match(parts[0])
        ):
            parts[0] = member.lower().translate(str.maketrans("", "", "._-"))

        return ".".join(parts)

    @computed_field
    @property
    def family(self) -> _T:
        if codec := (
            VideoCodecFamily.match(self.original)
            or AudioCodecFamily.match(self.original)
        ):
            return codec  # ty: ignore[invalid-return-type]
        raise ValueError(self.original)
