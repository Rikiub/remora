import importlib
import subprocess
from functools import cache
from pathlib import Path
from shutil import which

from remora.exceptions import FFmpegError, FFmpegNotFoundError, FFprobeNotFoundError
from remora.models.types import StrPath

# Directories


def get_ffmpeg_dir(ffmpeg_dir: StrPath | None = None) -> Path:
    """Get FFmpeg and FFprobe binaries directory from wheel, system or provided path.

    Raises:
        FFmpegError: FFmpeg binary not found.
    """

    if ffmpeg_dir:
        return validate_ffmpeg_dir(Path(ffmpeg_dir))
    else:
        ffmpeg_dir = find_wheel_ffmpeg_dir() or find_system_ffmpeg_dir()

        if not ffmpeg_dir:
            raise FFmpegNotFoundError()
        return ffmpeg_dir


@cache
def find_wheel_ffmpeg_dir() -> Path | None:
    """Find FFmpeg and FFprobe binaries directory from wheel."""

    try:
        package = importlib.import_module("ffmpeg")

        ffmpeg = validate_ffmpeg(package.FFMPEG_PATH)
        ffprobe = validate_ffprobe(package.FFPROBE_PATH)

        # Both FFmpeg and FFprobe binaries must be in the same directory
        if ffmpeg.parent != ffprobe.parent:
            return None

        return ffmpeg.parent
    except ImportError:
        return None


@cache
def find_system_ffmpeg_dir() -> Path | None:
    """Find FFmpeg and FFprobe binaries directory from system."""

    try:
        ffmpeg = which("ffmpeg")
        ffprobe = which("ffprobe")

        ffmpeg = validate_ffmpeg(ffmpeg)
        ffprobe = validate_ffprobe(ffprobe)

        # Both FFmpeg and FFprobe binaries must be in the same directory
        if ffmpeg.parent != ffprobe.parent:
            return None

        return ffmpeg.parent
    except (FFmpegNotFoundError, FFprobeNotFoundError):
        return None


def validate_ffmpeg_dir(ffmpeg_dir: StrPath | None) -> Path:
    if not ffmpeg_dir:
        raise FFmpegNotFoundError("FFmpeg directory not found.")
    ffmpeg_dir = Path(ffmpeg_dir)

    ffmpeg = which("ffmpeg", path=ffmpeg_dir)
    ffprobe = which("ffprobe", path=ffmpeg_dir)

    ffmpeg = validate_ffmpeg(ffmpeg)
    ffprobe = validate_ffprobe(ffprobe)

    if ffmpeg.parent != ffprobe.parent:
        raise FFmpegError(
            "Both ffmpeg and ffprobe binaries must be in the same directory."
        )

    return ffmpeg_dir


@cache
def _validate_ffmpeg_dir(ffmpeg_dir: Path) -> Path:
    ffmpeg = which("ffmpeg", path=ffmpeg_dir)
    ffprobe = which("ffprobe", path=ffmpeg_dir)

    ffmpeg = validate_ffmpeg(ffmpeg)
    ffprobe = validate_ffprobe(ffprobe)

    if ffmpeg.parent != ffprobe.parent:
        raise FFmpegError(
            "Both ffmpeg and ffprobe binaries must be in the same directory."
        )

    return ffmpeg_dir


# Single binaries


def validate_ffmpeg(ffmpeg_path: StrPath | None) -> Path:
    """Validate provided FFmpeg binary.

    Raises:
        FFmpegNotFoundError: Issue when try to execute the binary.
    """

    # Ensure the path is not None
    if not ffmpeg_path:
        raise FFmpegNotFoundError("FFmpeg executable not found.")

    return _validate_ffmpeg(Path(ffmpeg_path))


@cache
def _validate_ffmpeg(ffmpeg_path: Path) -> Path:
    """Validate provided FFmpeg binary."""

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


def validate_ffprobe(ffprobe_path: StrPath | None) -> Path:
    """Validate provided FFprobe binary.

    Raises:
        FFmpegNotFoundError: Issue when try to execute the binary.
    """

    # Ensure the path is not None
    if not ffprobe_path:
        raise FFprobeNotFoundError("FFprobe executable not found.")

    return _validate_ffprobe(Path(ffprobe_path))


@cache
def _validate_ffprobe(ffprobe_path: Path) -> Path:
    """Validate provided FFprobe binary."""

    try:
        result = subprocess.run(
            [ffprobe_path, "-version"],
            capture_output=True,
            text=True,
            timeout=3,  # Prevents hanging if the binary waits for user input
            check=True,  # Raises an error if the exit code is not 0
        )

        # result.stdout is explicitly checked here since text=True places the output there
        if "ffprobe version" not in str(result):
            raise FFprobeNotFoundError(
                f"'{ffprobe_path.name}' is a binary, but it doesn't appear to be FFprobe."
            )
    except subprocess.TimeoutExpired:
        raise FFprobeNotFoundError(
            f"'{ffprobe_path.name}' binary timed out. This is likely not FFprobe."
        )
    except subprocess.CalledProcessError:
        raise FFprobeNotFoundError(
            f"'{ffprobe_path.name}' binary crashed or returned a non-zero exit code."
        )
    except OSError:
        raise FFprobeNotFoundError(
            f"'{ffprobe_path.name}' OS failed to execute the file."
        )

    return ffprobe_path
