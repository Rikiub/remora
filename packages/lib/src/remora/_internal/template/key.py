from pydantic import BaseModel

from remora._internal.template.generator import get_keys as _get_keys
from remora.exceptions import OutputTemplateError
from remora.models.media.item import Media
from remora.models.media.list import Playlist


class PlaylistNested(BaseModel):
    playlist: Playlist


# Generate and keep copy
_MODELS = [Media, PlaylistNested]
_KEYS = _get_keys(_MODELS)
_KEYS_FLAT = _get_keys(_MODELS, True)


# Public functions
def get_keys(flat: bool = False) -> set[str]:
    return _KEYS_FLAT if flat else _KEYS


def validate_key(key: str, flat: bool = False) -> str:
    if key not in get_keys(flat):
        raise OutputTemplateError(f"Key '{key}' is invalid")
    return key
