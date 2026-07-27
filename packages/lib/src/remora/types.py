from os import PathLike
from typing import Literal

from pydantic.networks import HttpUrl

# Quality
AudioQuality = Literal[128, 256, 360]
VideoQuality = Literal[144, 240, 360, 480, 720, 1080]
StreamQuality = VideoQuality | AudioQuality

# Generics
StrPath = PathLike[str] | str
StrUrl = HttpUrl | str

# Extra
APP_NAME = "remora"
DEFAULT_TEMPLATE = "{uploader.name} - {title}"
DEFAULT_RETRIES = 3
