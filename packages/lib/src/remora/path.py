import atexit
import os
import shutil
import tempfile

from anyio import Path
from anyio.to_thread import run_sync

from remora.types import APP_NAME, StrPath

TMP_DIR = Path(tempfile.mkdtemp(prefix=f"{APP_NAME}-"))


# Directories
async def get_cache_dir() -> Path:
    dir = Path(tempfile.gettempdir(), APP_NAME)
    await dir.mkdir(parents=True, exist_ok=True)
    return dir


# Functions
async def get_tempfile() -> Path:
    with tempfile.NamedTemporaryFile(dir=TMP_DIR, delete=False) as file:
        return Path(file.name)


async def get_ffmpeg(ffmpeg_path: StrPath | None = None) -> Path | None:
    if ffmpeg_path:
        ffmpeg_path = Path(ffmpeg_path)
    else:
        ffmpeg_path = await get_global_ffmpeg()

    if ffmpeg_path and not await check_executable_exists(ffmpeg_path):
        raise FileNotFoundError(f"'{ffmpeg_path.name}' is not a FFmpeg executable.")

    return ffmpeg_path


async def get_global_ffmpeg() -> Path | None:
    path = await run_sync(shutil.which, "ffmpeg")

    if path:
        return Path(path)
    else:
        return None


async def check_executable_exists(file: StrPath) -> bool:
    file = Path(file)
    has_access = await run_sync(os.access, file, os.X_OK)

    if await file.is_file() and has_access:
        return True
    else:
        return False


def _clear_tempdir():
    """Delete global temporary directory."""

    shutil.rmtree(TMP_DIR)


atexit.register(_clear_tempdir)
