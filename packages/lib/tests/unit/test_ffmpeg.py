from pathlib import Path

import pytest

from remora.exceptions import FFmpegNotFoundError
from remora.ffmpeg import (
    _validate_ffmpeg,
    _validate_ffmpeg_dir,
    _validate_ffprobe,
    find_system_ffmpeg_dir,
    find_wheel_ffmpeg_dir,
    validate_ffmpeg,
)

MODULE = "remora.ffmpeg"


@pytest.fixture(autouse=True)
def clear_caches():
    """Clears functools caches before every test to prevent state leakage."""
    find_wheel_ffmpeg_dir.cache_clear()
    find_system_ffmpeg_dir.cache_clear()
    _validate_ffmpeg.cache_clear()
    _validate_ffprobe.cache_clear()
    _validate_ffmpeg_dir.cache_clear()


def test_validate_ffmpeg_none():
    """Test that passing None raises the correct error."""
    with pytest.raises(FFmpegNotFoundError, match="FFmpeg executable not found."):
        validate_ffmpeg(None)


def test_validate_ffmpeg_success(mocker):
    """Test a successful FFmpeg validation."""

    # Mock subprocess.run
    mocker.patch("subprocess.run", return_value="ffmpeg version")

    ffmpeg_path = Path("local_ffmpeg")
    validated_path = validate_ffmpeg(ffmpeg_path)

    # Verify the return value
    assert validated_path == ffmpeg_path


@pytest.mark.skip("WIP")
def test_found_system_ffmpeg(mocker):
    """Test ffmpeg binary search."""

    BINARY = "ffmpeg"
    mocker.patch(f"{MODULE}.which", return_value=BINARY)
    mocker.patch("subprocess.run", return_value="ffmpeg version")

    ffmpeg_path = find_system_ffmpeg_dir()
    compare_path = Path(BINARY)

    assert ffmpeg_path == compare_path


def test_missing_system_ffmpeg(mocker):
    """Test ffmpeg binary missed."""
    mocker.patch(f"{MODULE}.which", return_value=None)

    path = find_system_ffmpeg_dir()
    assert path is None
