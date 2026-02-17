import atexit
import os
import shutil
import tempfile
from functools import cache
from pathlib import Path

from remora.exceptions import FFmpegNotFoundError
from remora.types import APP_NAME, StrPath

TMP_DIR = Path(tempfile.mkdtemp(prefix=f"{APP_NAME}-"))


# Directories
def get_cache_dir() -> Path:
    dir = Path(tempfile.gettempdir(), APP_NAME)
    dir.mkdir(parents=True, exist_ok=True)
    return dir


# Functions
def get_tempfile() -> Path:
    with tempfile.NamedTemporaryFile(dir=TMP_DIR, delete=False) as file:
        return Path(file.name)


def get_ffmpeg(ffmpeg_path: StrPath | None = None) -> Path:
    ffmpeg_path = ffmpeg_path or find_global_ffmpeg()

    if not ffmpeg_path:
        raise FileNotFoundError("FFmpeg path is needed for use processors.")

    return validate_ffmpeg(ffmpeg_path)


@cache
def find_global_ffmpeg() -> Path | None:
    path = shutil.which("ffmpeg")

    if path:
        return Path(path)
    else:
        return None


@cache
def validate_ffmpeg(ffmpeg_path: StrPath | None) -> Path:
    if not ffmpeg_path:
        raise FFmpegNotFoundError("FFmpeg executable not founded.")

    ffmpeg_path = Path(ffmpeg_path)

    if not check_executable_exists(ffmpeg_path):
        raise FFmpegNotFoundError(f"'{ffmpeg_path.name}' is not a FFmpeg executable.")

    return Path(ffmpeg_path)


def check_executable_exists(file: StrPath) -> bool:
    file = Path(file)

    if file.is_file() and os.access(file, os.X_OK):
        return True
    else:
        return False


def _clear_tempdir():
    """Delete global temporary directory."""

    shutil.rmtree(TMP_DIR)


atexit.register(_clear_tempdir)
