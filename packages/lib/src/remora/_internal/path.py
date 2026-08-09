import atexit
import shutil
import tempfile
from pathlib import Path

from remora.types import LIBRAY_NAME

TMP_DIR = Path(tempfile.mkdtemp(prefix=f"{LIBRAY_NAME}-"))


def get_cache_dir() -> Path:
    dir = Path(tempfile.gettempdir(), LIBRAY_NAME)
    dir.mkdir(parents=True, exist_ok=True)
    return dir


def get_tempfile() -> Path:
    with tempfile.NamedTemporaryFile(dir=TMP_DIR, delete=False) as file:
        return Path(file.name)


def _clear_tempdir():
    """Delete global temporary directory."""

    shutil.rmtree(TMP_DIR)


atexit.register(_clear_tempdir)
