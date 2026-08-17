import atexit
import shutil
import tempfile
from pathlib import Path

from platformdirs import PlatformDirs

from remora.types import LIBRAY_NAME

_DIRS = PlatformDirs(LIBRAY_NAME, appauthor=False, ensure_exists=True)


def get_config_dir() -> Path:
    """Get config directory of the library."""
    return _DIRS.user_config_path


def get_cache_dir() -> Path:
    """Get cache directory of the library."""
    return _DIRS.user_cache_path


# Temporary directory exclusive of the current session
# Deleted automatically on exit


def get_temp_dir() -> Path:
    return _DIRS.user_runtime_path


def create_temp_file() -> Path:
    """Create and return file in the temporary directory."""
    with tempfile.NamedTemporaryFile(dir=get_temp_dir(), delete=False) as file:
        return Path(file.name)


def _clear_session_temp_dir():
    """Delete session temporary directory."""

    shutil.rmtree(get_temp_dir())


atexit.register(_clear_session_temp_dir)
