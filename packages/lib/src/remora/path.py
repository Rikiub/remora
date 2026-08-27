import atexit
import tempfile
from pathlib import Path

from platformdirs import PlatformDirs

import remora

__all__ = [
    "create_temp_file",
    "get_cache_dir",
    "get_config_dir",
    "get_log_dir",
    "get_session_temp_dir",
]

_DIRS = PlatformDirs(remora.__name__, appauthor=False, ensure_exists=True)


def get_config_dir() -> Path:
    """Get config directory of the library."""
    return _DIRS.user_config_path


def get_cache_dir() -> Path:
    """Get cache directory of the library."""
    return _DIRS.user_cache_path


def get_log_dir() -> Path:
    """Get log directory of the library."""
    return _DIRS.user_log_path


# Temporary directory exclusive of the current session
# Deleted automatically on exit

_session_temp_dir: tempfile.TemporaryDirectory | None = None


def get_session_temp_dir() -> Path:
    """Get temporary directory for the current session."""
    global _session_temp_dir

    if not _session_temp_dir:
        _session_temp_dir = tempfile.TemporaryDirectory(dir=_DIRS.user_runtime_path)

    return Path(_session_temp_dir.name)


def create_temp_file() -> Path:
    """Create and return file in the temporary directory."""
    with tempfile.NamedTemporaryFile(dir=get_session_temp_dir(), delete=False) as file:
        return Path(file.name)


def _clear_session_temp_dir():
    """Delete session temporary directory."""
    global _session_temp_dir

    if _session_temp_dir:
        _session_temp_dir.cleanup()
        _session_temp_dir = None


atexit.register(_clear_session_temp_dir)
