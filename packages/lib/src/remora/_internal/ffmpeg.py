import shutil
import subprocess
from functools import cache
from pathlib import Path

from remora.exceptions import FFmpegNotFoundError
from remora.types import StrPath


def get_ffmpeg(ffmpeg_path: StrPath | None = None) -> Path:
    """Get FFmpeg binary from path or system.

    Raises:
        FFmpegNotFoundError: FFmpeg binary not found.
    """

    ffmpeg_path = ffmpeg_path or find_global_ffmpeg()

    if not ffmpeg_path:
        raise FFmpegNotFoundError("FFmpeg path not provided.")

    return validate_ffmpeg(ffmpeg_path)


@cache
def find_global_ffmpeg() -> Path | None:
    """Try to find FFmpeg binary from system."""

    path = shutil.which("ffmpeg")
    return Path(path) if path else None


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
