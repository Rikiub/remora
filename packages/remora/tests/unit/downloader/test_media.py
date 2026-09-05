from collections.abc import Callable
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture
from typing_extensions import override

import remora.downloader.pipeline.media as downloader
from remora.downloader.pipeline.media import MediaDownloader
from remora.downloader.stream.batch import BatchStreamDownloader
from remora.models.container import CodecInfo
from remora.models.media import ExtractorInfo
from remora.models.media.item import Media
from remora.models.metadata.subtitle import ExternalSubtitle, SubtitleList
from remora.models.metadata.thumbnail import Thumbnail, ThumbnailList
from remora.models.options.download import DownloadOptions
from remora.models.progress import MediaStarted
from remora.models.progress.media import (
    MediaCompleted,
    MediaDownloading,
    MediaEnded,
    MediaProcessing,
)
from remora.models.progress.stream import (
    BatchStreamCompleted,
    BatchStreamDownloading,
)
from remora.models.stream.item import AudioInfo, AudioStream, VideoInfo, VideoStream
from remora.processor import MediaProcessor

MODULE_PATH = downloader.__name__


# Fake dependencies
class FakeBatchDownloader(BatchStreamDownloader):
    """Mocks the async generator for stream downloads."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @override
    async def _run_pipeline(self):
        await self._emit(BatchStreamDownloading(streams=[]))
        await self._emit(
            BatchStreamCompleted(paths=["/tmp/video.mp4", "/tmp/audio.mp4"])
        )


MockPipeline = Callable[[Media], MediaDownloader]


# Fixtures
@pytest.fixture
def dummy_media() -> Media:
    """Full media rich of placeholder metadata and streams."""
    URL = "https://example.com/video"

    return Media(
        extractor=ExtractorInfo(id="Youtube", name="youtube"),
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
                container="mp4",
                video=VideoInfo(codec=CodecInfo(original="vp9")),
            ),
            AudioStream(
                id="2",
                url=URL,
                protocol="https",
                size_type="exact",
                size_bytes=4000,
                container="m4a",
                audio=AudioInfo(codec=CodecInfo(original="m4a")),
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

    def _(media: Media) -> MediaDownloader:
        # Mock File System Paths
        mocker.patch.object(
            downloader,
            downloader.create_temp_file.__name__,
            return_value=tmp_path / "temp",
        )

        # Mock Shutil to prevent file moving
        mocker.patch.object(
            downloader.shutil,
            downloader.shutil.move.__name__,
        )

        # Mock Stream Selectors to return dummy streams
        try:
            video = media.streams.videos()[0]
        except IndexError:
            video = None

        try:
            audio = media.streams.audios()[0]
        except IndexError:
            audio = None

        mock_selector = mocker.patch.object(
            downloader,
            downloader.StreamSelector.__name__,
        )
        mock_selector.return_value.resolve.return_value = [video, audio]

        # Mock stream downloader
        mocker.patch.object(
            downloader,
            downloader.BatchStreamDownloader.__name__,
            FakeBatchDownloader,
        )

        # Mock metadata downloaders
        mocker.patch.object(
            downloader,
            downloader._download_thumbnail.__name__,
            new_callable=AsyncMock,
            return_value=tmp_path / "thumbnail.jpg",
        )
        mocker.patch.object(
            downloader,
            downloader._download_subtitle.__name__,
            new_callable=AsyncMock,
            return_value=[tmp_path / "subtitle.srt"],
        )

        # Init pipeline
        pipeline = MediaDownloader(
            media=media,
            download_options=DownloadOptions(
                output_template=tmp_path,
                embed_metadata=True,
            ),
        )
        return pipeline

    return _


# Tests
async def test_download_states(
    mock_pipeline: MockPipeline,
    dummy_media: Media,
):
    """
    Test that the pipeline correctly extracts, downloads and completes
    from video and audio.
    """

    downloader = mock_pipeline(dummy_media)

    # Consume the async generator
    async with downloader as progress:
        states = [type(state) async for state in progress]

    assert MediaStarted in states
    assert MediaDownloading in states
    assert MediaProcessing in states
    assert MediaCompleted in states
    assert MediaEnded in states


# Media Processor
@pytest.mark.skip("Hard to test right now")
async def test_processor_merge(
    mock_pipeline: MockPipeline,
    mock_processor: AsyncMock,
    dummy_media: Media,
):
    """Test that the pipeline merges the streams."""

    downloader = mock_pipeline(dummy_media)

    # Consume the async generator
    async with downloader as progress:
        [_ async for _ in progress]

    # Verify specific inner methods were called
    mock_processor.merge_streams.assert_called_once()


@pytest.mark.skip("Hard to test right now")
async def test_processor_no_merge(
    mock_pipeline: MockPipeline,
    mock_processor: AsyncMock,
    dummy_media: Media,
):
    """Test that the pipeline NOT merges the streams."""

    # Get media proccesor
    processor: MediaProcessor = mock_processor()

    # Init pipeline
    pipeline = mock_pipeline(dummy_media)

    # Set only ONE stream to avoid merge streams
    pipeline.media.streams = pipeline.media.streams.audio_only()  # ty: ignore[invalid-assignment]

    # Consume the async generator
    async with pipeline as progress:
        async for _ in progress:
            pass

    # Verify specific inner methods were called
    processor.merge_streams.assert_not_called()  # ty: ignore[unresolved-attribute]


@pytest.mark.skip("Hard to test right now")
async def test_full_processor_metadata(
    mock_pipeline: MockPipeline,
    mock_processor: AsyncMock,
    dummy_media: Media,
):
    """Test that the pipeline correctly applies post-processing."""

    # Get media proccesor
    processor: MediaProcessor = mock_processor()

    # Init pipeline
    pipeline = mock_pipeline(dummy_media)

    # Consume the async generator
    async with pipeline as progress:
        async for _ in progress:
            pass

    # Verify specific inner methods were called
    processor.embed_metadata.assert_called_once()  # ty: ignore[unresolved-attribute]
    processor.embed_thumbnail.assert_called_once()  # ty: ignore[unresolved-attribute]


@pytest.mark.skip("Hard to test right now")
async def test_empty_processor_metadata(
    mock_pipeline: MockPipeline,
    mock_processor: AsyncMock,
    dummy_media: Media,
):
    """Test that the pipeline correctly extracts, downloads and completes."""

    # Get media proccesor
    processor: MediaProcessor = mock_processor()

    # Init pipeline
    # And remove metadata
    dummy_media.subtitles = SubtitleList()
    dummy_media.thumbnails = ThumbnailList()

    pipeline = mock_pipeline(dummy_media)

    # Consume the async generator
    async with pipeline as progress:
        async for _ in progress:
            pass

    # Verify specific inner methods were NOT called
    processor.embed_metadata.assert_not_called()  # ty: ignore[unresolved-attribute]
    processor.embed_thumbnail.assert_not_called()  # ty: ignore[unresolved-attribute]
