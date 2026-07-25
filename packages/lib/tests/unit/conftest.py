from collections.abc import Callable
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from remora._internal.processor import MediaProcessor
from remora.models.media.item import Media
from remora.models.metadata.subtitle import ExternalSubtitle
from remora.models.metadata.thumbnail import Thumbnail
from remora.models.stream.item import AudioInfo, AudioStream, VideoInfo, VideoStream


@pytest.fixture
def mock_processor(mocker: MockerFixture, tmp_path: Path) -> Callable:
    """Mocks FFmpeg binary, filesystem and return the media processor."""

    # Keep track of mocked modules for the current test
    patched_modules = {}

    def func(module: str) -> MediaProcessor:
        # If we already mocked this module in the current test, return the existing mock
        if module in patched_modules:
            return patched_modules[module]

        # Mock FFmpeg presence
        mocker.patch(f"{module}.get_ffmpeg", return_value=Path("/usr/bin/ffmpeg"))

        # Mock MediaProcessor
        mock_class = mocker.patch(
            f"{module}.{MediaProcessor.__name__}",
            autospec=True,
        )

        mock_instance = mock_class.return_value
        mock_instance.file_path = tmp_path / "processed.mp4"

        # Cache it to prevent InvalidSpecError on duplicate calls
        patched_modules[module] = mock_instance

        return mock_instance

    return func


@pytest.fixture
def dummy_media() -> Media:
    """Full media rich of placeholder metadata and streams."""
    URL = "https://example.com/video"

    return Media(
        extractor="Youtube",
        id="test_123",
        title="Mock Video",
        url="https://youtube.com/watch?v=test",
        thumbnails=[
            Thumbnail(
                id="1",
                url=URL,
            )
        ],
        subtitles=[
            ExternalSubtitle(
                url=URL,
                name="English",
                language="en",
                extension="vtt",
            ),
        ],
        streams=[
            VideoStream(
                id="1",
                url=URL,
                protocol="https",
                size_type="exact",
                size_bytes=50000,
                extension="mp4",
                video=VideoInfo(codec="vp9"),
            ),
            AudioStream(
                id="2",
                url=URL,
                protocol="https",
                size_type="exact",
                size_bytes=4000,
                extension="m4a",
                audio=AudioInfo(codec="m4a"),
            ),
        ],
    )
