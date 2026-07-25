from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from remora._internal.downloader.pipeline import DownloadPipeline
from remora._internal.downloader.stream.batch import BatchStreamDownloader
from remora.models.download_options import DownloadOptions
from remora.models.event.media import (
    MediaCompleted,
    MediaDownloading,
    MediaExtracting,
    MediaProcessing,
)
from remora.models.event.stream import BatchStreamCompleted, BatchStreamDownloading
from remora.models.media.item import Media
from remora.models.metadata.subtitle import ExternalSubtitle
from remora.models.metadata.thumbnail import Thumbnail
from remora.models.stream.item import AudioInfo, AudioStream, VideoInfo, VideoStream

MODULE_PATH = "remora._internal.downloader.pipeline"
URL = "https://example.com"


# Fake dependencies
class FakeBatchDownloader(BatchStreamDownloader):
    """Mocks the async generator for stream downloads."""

    def __init__(self, *args, **kwargs):
        pass

    async def download(self):
        yield BatchStreamDownloading(streams=[])
        yield BatchStreamCompleted(
            video_path="/tmp/video.mp4",
            audio_path="/tmp/audio.mp4",
        )


# Fixtures
@pytest.fixture
def dummy_media() -> Media:
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


@pytest.fixture
def pipeline(
    mocker: MockerFixture,
    mocker_processor: AsyncMock,
    dummy_media: Media,
    tmp_path: Path,
) -> DownloadPipeline:
    """Mocks all network, filesystem, and subprocess calls."""

    # Mock Processor Dependencies
    mocker_processor(MODULE_PATH)

    # Mock File System Paths
    mocker.patch(f"{MODULE_PATH}.get_tempfile", return_value=tmp_path / "temp")

    # Mock Shutil to prevent file moving
    mocker.patch(f"{MODULE_PATH}.shutil.move")

    # Mock Stream Selectors to return dummy streams
    mock_selector = mocker.patch(f"{MODULE_PATH}.StreamSelector")
    mock_selector.return_value.resolve.return_value = (
        VideoStream(
            id="v1",
            url=URL,
            extension="mp4",
            protocol="https",
            video=VideoInfo(codec="vp9"),
        ),
        AudioStream(
            id="a1",
            url=URL,
            extension="m4a",
            protocol="https",
            audio=AudioInfo(codec="opus"),
        ),
    )

    # Mock the Heavy Downloaders
    mocker.patch(f"{MODULE_PATH}.BatchStreamDownloader", FakeBatchDownloader)
    mocker.patch(
        f"{MODULE_PATH}.download_thumbnail",
        new_callable=AsyncMock,
        return_value=tmp_path / "thumbnail.jpg",
    )
    mocker.patch(
        f"{MODULE_PATH}.download_subtitles",
        new_callable=AsyncMock,
        return_value=[tmp_path / "subtitle.srt"],
    )

    # Arrange
    mock_extractor = AsyncMock()
    mock_extractor.extract.return_value = dummy_media

    # Init pipeline
    pipeline = DownloadPipeline(
        media=dummy_media,
        extractor=mock_extractor,
        config=DownloadOptions(output_template=tmp_path, embed_metadata=True),
    )

    return pipeline


# Tests
async def test_download_pipeline(
    pipeline: DownloadPipeline, mocker_processor: AsyncMock
):
    """
    Test that the pipeline correctly extracts, downloads, processes, and completes
    without hitting the network or filesystem.
    """

    # Mock and get media proccesor
    processor = mocker_processor(MODULE_PATH)

    # Consume the async generator
    events = []

    async for event in pipeline.download():
        events.append(event)

    # Check that the event sequence is exactly as expected
    event_types = [type(e) for e in events]

    assert MediaExtracting in event_types
    assert MediaDownloading in event_types
    assert MediaProcessing in event_types
    assert MediaCompleted in event_types

    # Check the final completion event
    completion_event = events[-1]
    assert isinstance(completion_event, MediaCompleted)
    assert completion_event.result == "success"

    # Verify specific inner methods were called
    processor.merge_streams.assert_called_once()
    processor.embed_metadata.assert_called_once()
    processor.embed_thumbnail.assert_called_once()
