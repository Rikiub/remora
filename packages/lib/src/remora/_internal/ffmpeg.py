import importlib
import subprocess
from functools import cache
from pathlib import Path
from shutil import which

from remora.exceptions import FFmpegNotFoundError
from remora.types import StrPath


def get_ffmpeg(ffmpeg_path: StrPath | None = None) -> Path:
    """Get FFmpeg binary from path or system.

    Raises:
        FFmpegNotFoundError: FFmpeg binary not found.
    """

    ffmpeg_path = ffmpeg_path or find_internal_ffmpeg() or find_system_ffmpeg()

    if not ffmpeg_path:
        raise FFmpegNotFoundError("FFmpeg path not provided.")

    return validate_ffmpeg(ffmpeg_path)


@cache
def find_internal_ffmpeg() -> Path | None:
    """Try find FFmpeg binary from dependency."""

    try:
        package = importlib.import_module("imageio_ffmpeg")

        ffmpeg = package.get_ffmpeg_exe()
        ffmpeg = validate_ffmpeg(ffmpeg)

        return ffmpeg
    except ImportError:
        return None


@cache
def find_system_ffmpeg() -> Path | None:
    """Try find FFmpeg binary from system."""

    try:
        ffmpeg = which("ffmpeg")
        ffmpeg = validate_ffmpeg(ffmpeg)

        return ffmpeg
    except FFmpegNotFoundError:
        return None


@cache
def validate_ffmpeg(ffmpeg_path: StrPath | None) -> Path:
    """Validate provided FFmpeg binary.

    Raises:
        FFmpegNotFoundError: Issue when try to execute the binary.
    """

    # Ensure the path is not None
    if not ffmpeg_path:
        raise FFmpegNotFoundError("FFmpeg executable not found.")

    ffmpeg_path = Path(ffmpeg_path)

    # Run it and check the output.
    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=3,  # Prevents hanging if the binary waits for user input
            check=True,  # Raises an error if the exit code is not 0
        )

        if "ffmpeg version" not in str(result):
            raise FFmpegNotFoundError(
                f"'{ffmpeg_path.name}' is a binary, but it doesn't appear to be FFmpeg."
            )
    except subprocess.TimeoutExpired:
        raise FFmpegNotFoundError(
            f"'{ffmpeg_path.name}' binary timed out. This is likely not FFmpeg."
        )
    except subprocess.CalledProcessError:
        raise FFmpegNotFoundError(
            f"'{ffmpeg_path.name}' binary crashed or returned a non-zero exit code."
        )
    except OSError:
        raise FFmpegNotFoundError(
            f"'{ffmpeg_path.name}' OS failed to execute the file."
        )

    return ffmpeg_path
