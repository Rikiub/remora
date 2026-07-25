from pathlib import Path

import pytest

from remora._internal.ffmpeg import find_global_ffmpeg, validate_ffmpeg
from remora.exceptions import FFmpegNotFoundError


@pytest.fixture(autouse=True)
def clear_caches():
    """Clears functools caches before every test to prevent state leakage."""
    find_global_ffmpeg.cache_clear()
    validate_ffmpeg.cache_clear()


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


def test_founded_system_ffmpeg(mocker):
    """Test ffmpeg binary search."""

    BINARY = "ffmpeg"
    mocker.patch("shutil.which", return_value=BINARY)

    compare_path = Path(BINARY)
    ffmpeg_path = find_global_ffmpeg()

    assert ffmpeg_path == compare_path


def test_missing_system_ffmpeg(mocker):
    """Test ffmpeg binary missed."""
    mocker.patch("shutil.which", return_value=None)

    path = find_global_ffmpeg()
    assert path is None
