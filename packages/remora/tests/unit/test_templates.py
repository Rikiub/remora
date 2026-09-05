import pytest

from remora.models.container import CodecInfo
from remora.models.media import ExtractorInfo
from remora.models.media.item import Media
from remora.models.media.list import Playlist
from remora.models.metadata import Channel, DateMetadata, Metrics, Uploader
from remora.models.stream.item import VideoInfo, VideoStream
from remora.template import format_template


@pytest.fixture
def dummy_video_stream() -> VideoStream:
    """Media rich of placeholder metadata."""
    return VideoStream(
        id="1",
        url="https://example.com/stream",
        protocol="https",
        size_type="exact",
        size_bytes=50000,
        container="mp4",
        video=VideoInfo(
            codec=CodecInfo(original="vp9"),
            bitrate=300,
        ),
    )


@pytest.fixture
def dummy_media() -> Media:
    """Media rich of placeholder metadata."""
    return Media(
        extractor=ExtractorInfo(id="ExtractorMedia", name="extractor:media"),
        id="1",
        title="Media Title",
        url="https://example.com/media",
        uploader=Uploader(
            name="Uploader Name",
            id="Uploader Id",
            url="https://example.com/uploader",
        ),
        channel=Channel(
            name="Channel Name",
            id="Channel Id",
            url="https://example.com/channel",
            is_verified=True,
            followers=300,
        ),
        metrics=Metrics(
            views=300,
            likes=1200,
            comments=50,
        ),
    )


@pytest.fixture
def dummy_playlist() -> Playlist:
    """Playlist rich of placeholder metadata."""
    return Playlist(
        id="1",
        url="https://example.com/playlist",
        title="Playlist Title",
        extractor=ExtractorInfo(id="ExtractorPlaylist", name="extractor:playlist"),
        date=DateMetadata(
            modified="2026-05-02T12:00:00",
            uploaded="2026-05-02T12:00:00",
            released="2026-05-02T12:00:00",
        ),
        uploader=Uploader(
            name="Uploader Name",
            id="Uploader Id",
            url="https://example.com/uploader",
        ),
        channel=Channel(
            name="Channel Name",
            id="Channel Id",
            url="https://example.com/channel",
            is_verified=True,
            followers=300,
        ),
    )


@pytest.fixture
def format(
    dummy_media: Media,
    dummy_playlist: Playlist,
    dummy_video_stream: VideoStream,
):
    def _(template: str):
        return format_template(
            output_template=template,
            stream=dummy_video_stream,
            media=dummy_media,
            playlist=dummy_playlist,
        )

    return _


def test_media(format):
    assert format("{extractor.id}") == "ExtractorMedia"
    assert format("{extractor.name}") == "extractor-media"
    assert format("{title}") == "Media Title"

    assert format("{uploader.name}") == "Uploader Name"
    assert format("{uploader.id}") == "Uploader Id"

    assert format("{channel.name}") == "Channel Name"
    assert format("{channel.id}") == "Channel Id"
    assert format("{channel.is_verified}") == "True"
    assert format("{channel.followers}") == "300"


def test_playlist(format):
    assert format("{playlist.extractor.id}") == "ExtractorPlaylist"
    assert format("{playlist.extractor.name}") == "extractor-playlist"
    assert format("{playlist.title}") == "Playlist Title"

    assert format("{playlist.uploader.name}") == "Uploader Name"
    assert format("{playlist.uploader.id}") == "Uploader Id"

    assert format("{playlist.channel.name}") == "Channel Name"
    assert format("{playlist.channel.id}") == "Channel Id"
    assert format("{playlist.channel.is_verified}") == "True"
    assert format("{playlist.channel.followers}") == "300"
