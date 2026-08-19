from os import PathLike

from pydantic.networks import HttpUrl

# Generics
StrPath = PathLike[str] | str
StrUrl = HttpUrl | str

# Extra
LIBRAY_NAME = "remora"
DEFAULT_TEMPLATE = "{uploader.name} - {title}"
DEFAULT_WORKERS = 5
DEFAULT_RETRIES = 3
