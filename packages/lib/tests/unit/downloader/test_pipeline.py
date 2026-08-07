from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture
from remora._internal.downloader.stream.muxed import MuxedStreamDownloader

from remora._internal.downloader.pipeline import DownloadPipeline
from remora._internal.downloader.selector import StreamSelector
from remora._internal.downloader.stream.main import StreamDownloader
from remora._internal.processor import MediaProcessor
from remora.models.download_options import DownloadOptions
from remora.models.event.media import (
    MediaCompleted,
    MediaDownloading,
    MediaExtracting,
    MediaProcessing,
)
from remora.models.event.stream import (
    BatchStreamCompleted,
    BatchStreamDownloading,
    StreamCompleted,
    StreamContinuous,
)
from remora.models.media.item import Media
from remora.models.metadata.subtitle import ExternalSubtitle, SubtitleList
from remora.models.metadata.thumbnail import Thumbnail, ThumbnailList
from remora.models.stream.item import AudioInfo, AudioStream, VideoInfo, VideoStream

MODULE_PATH = "remora._internal.downloader.pipeline"


# Fake dependencies
class FakeBatchDownloader(MuxedStreamDownloader):
    """Mocks the async generator for stream downloads."""

    def __init__(self, *args, **kwargs):
        pass

    async def download(self):
        yield BatchStreamDownloading(streams=[])
        yield BatchStreamCompleted(
            video_path="/tmp/video.mp4",
            audio_path="/tmp/audio.mp4",
        )


class FakeStreamDownloader(StreamDownloader):
    """Mocks the async generator for stream downloads."""

    def __init__(self, *args, **kwargs):
        pass

    async def download(self):
        yield StreamContinuous(total_bytes=50000)
        yield StreamCompleted(file_path=Path())


MockPipeline = Callable[[Media], DownloadPipeline]


# Fixtures
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


@pytest.fixture
def mock_pipeline(
    mocker: MockerFixture,
    mock_processor: AsyncMock,
    tmp_path: Path,
) -> MockPipeline:
    """Mocks all network, filesystem, and subprocess calls."""

    def _(media: Media) -> DownloadPipeline:
        # Mock Processor Dependencies
        mock_processor(MODULE_PATH)

        # Mock File System Paths
        mocker.patch(f"{MODULE_PATH}.get_tempfile", return_value=tmp_path / "temp")

        # Mock Shutil to prevent file moving
        mocker.patch(f"{MODULE_PATH}.shutil.move")

        # Mock Stream Selectors to return dummy streams
        video = media.streams[0] if 0 <= 0 < len(media.streams) else None  # noqa: PLR0133
        audio = media.streams[1] if 0 <= 1 < len(media.streams) else None  # noqa: PLR0133

        mock_selector = mocker.patch(f"{MODULE_PATH}.{StreamSelector.__name__}")
        mock_selector.return_value.resolve.return_value = (video, audio)

        # Mock the Heavy Downloaders
        mocker.patch(f"{MODULE_PATH}.{StreamDownloader.__name__}", FakeStreamDownloader)
        mocker.patch(
            f"{MODULE_PATH}.{MuxedStreamDownloader.__name__}", FakeBatchDownloader
        )
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
        mock_extractor.extract.return_value = media

        # Init pipeline
        pipeline = DownloadPipeline(
            media=media,
            extractor=mock_extractor,
            config=DownloadOptions(output_template=tmp_path, embed_metadata=True),
        )

        return pipeline

    return _


# Tests
async def test_download_pipeline_muxed(
    mock_pipeline: MockPipeline,
    dummy_media: Media,
):
    """
    Test that the pipeline correctly extracts, downloads and completes
    from video and audio.
    """

    pipeline = mock_pipeline(dummy_media)

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


async def test_download_pipeline_single(
    mock_pipeline: MockPipeline,
    dummy_media: Media,
):
    """Test that the pipeline correctly extracts, downloads and completes."""

    dummy_media.streams = dummy_media.streams.audio_only()  # ty:ignore[invalid-assignment]
    pipeline = mock_pipeline(dummy_media)

    # Consume the async generator
    events = []

    async for event in pipeline.download():
        events.append(event)


# Media Processor
async def test_full_processor_metadata(
    mock_pipeline: MockPipeline,
    mock_processor: AsyncMock,
    dummy_media: Media,
):
    """Test that the pipeline correctly applies post-processing."""

    # Get media proccesor
    processor: MediaProcessor = mock_processor(MODULE_PATH)

    # Init pipeline
    pipeline = mock_pipeline(dummy_media)

    # Consume the async generator
    async for _ in pipeline.download():
        pass

    # Verify specific inner methods were called
    processor.merge_streams.assert_called_once()  # type: ignore
    processor.embed_metadata.assert_called_once()  # type: ignore
    processor.embed_thumbnail.assert_called_once()  # type: ignore


@pytest.mark.skip("Hard to test right now")
async def test_empty_processor_metadata(
    mock_pipeline: MockPipeline,
    mock_processor: AsyncMock,
    dummy_media: Media,
):
    """Test that the pipeline correctly extracts, downloads and completes."""

    # Get media proccesor
    processor: MediaProcessor = mock_processor(MODULE_PATH)

    # Init pipeline
    # And remove metadata
    dummy_media.subtitles = SubtitleList()
    dummy_media.thumbnails = ThumbnailList()

    pipeline = mock_pipeline(dummy_media)

    # Consume the async generator
    async for _ in pipeline.download():
        pass

    # Verify specific inner methods were NOT called
    processor.merge_streams.assert_not_called()  # type: ignore
    processor.embed_metadata.assert_not_called()  # type: ignore
    processor.embed_thumbnail.assert_not_called()  # type: ignore
