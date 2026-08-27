from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from remora import ffmpeg
from remora.exceptions import FFmpegNotFoundError


@pytest.fixture(autouse=True)
def clear_caches():
    """Clears functools caches before every test to prevent state leakage."""
    ffmpeg.find_wheel_ffmpeg_dir.cache_clear()
    ffmpeg.find_system_ffmpeg_dir.cache_clear()
    ffmpeg.get_system_ffmpeg_binary.cache_clear()
    ffmpeg.get_system_ffprobe_binary.cache_clear()
    ffmpeg._validate_ffmpeg.cache_clear()
    ffmpeg._validate_ffprobe.cache_clear()
    ffmpeg._validate_ffmpeg_dir.cache_clear()


def test_validate_ffmpeg_none():
    """Test that passing None raises the correct error."""
    with pytest.raises(FFmpegNotFoundError, match="FFmpeg executable not found."):
        ffmpeg.validate_ffmpeg(None)


def test_validate_ffmpeg_success(mocker: MockerFixture):
    """Test a successful FFmpeg validation."""

    # Mock subprocess.run
    mocker.patch("subprocess.run", return_value="ffmpeg version")

    ffmpeg_path = Path("local_ffmpeg")
    validated_path = ffmpeg.validate_ffmpeg(ffmpeg_path)

    # Verify the return value
    assert validated_path == ffmpeg_path


def test_found_system_ffmpeg(mocker: MockerFixture):
    """Test ffmpeg binary search."""

    # Mock binaries
    dir = Path("/usr/bin")
    ffmpeg_binary = dir / "ffmpeg"
    ffprobe_binary = dir / "ffprobe"

    mocker.patch.object(
        ffmpeg,
        ffmpeg.get_system_ffmpeg_binary.__name__,
        return_value=ffmpeg_binary,
    )
    mocker.patch.object(
        ffmpeg,
        ffmpeg.get_system_ffprobe_binary.__name__,
        return_value=ffprobe_binary,
    )

    # Mock binary validation
    mocker.patch.object(
        ffmpeg,
        ffmpeg._validate_ffmpeg.__name__,
        return_value=ffmpeg_binary,
    )
    mocker.patch.object(
        ffmpeg,
        ffmpeg._validate_ffprobe.__name__,
        return_value=ffprobe_binary,
    )

    ffmpeg_path = ffmpeg.find_system_ffmpeg_dir()
    compare_path = Path(dir)

    assert ffmpeg_path == compare_path


def test_missing_system_ffmpeg(mocker: MockerFixture):
    """Test ffmpeg binary missed."""
    mocker.patch.object(
        ffmpeg.shutil,
        ffmpeg.shutil.which.__name__,
        return_value=None,
    )

    path = ffmpeg.find_system_ffmpeg_dir()
    assert path is None
