from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from remora import ffmpeg as fpg
from remora import processor as prc
from remora.processor import MediaProcessor


@pytest.fixture
def mock_processor(mocker: MockerFixture, tmp_path: Path) -> MediaProcessor:
    """Mocks FFmpeg binary, filesystem and return the media processor."""

    # Mock FFmpeg presence
    ffmpeg_path = Path("/usr/bin")
    mocker.patch.object(
        fpg,
        fpg.find_wheel_ffmpeg_dir.__name__,
        return_value=ffmpeg_path,
    )
    mocker.patch.object(
        fpg,
        fpg.find_system_ffmpeg_dir.__name__,
        return_value=ffmpeg_path,
    )

    # Mock MediaProcessor
    processor = mocker.patch.object(
        prc,
        prc.MediaProcessor.__name__,
        autospec=True,
    )

    mock_instance = processor.return_value
    mock_instance.file_path = tmp_path / "processed.mp4"

    return mock_instance
