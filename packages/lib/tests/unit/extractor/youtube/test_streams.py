import pytest

from remora.models.stream.item import AudioStream, Stream, VideoStream
from remora.models.stream.list import StreamList


@pytest.fixture
async def streams(extract_ydl) -> StreamList:
    data = await extract_ydl("youtube/video.json")
    streams = data.streams

    assert isinstance(streams, StreamList)
    assert len(streams) > 0

    return streams


# Stream list validation
async def test_streams_and_types(streams: StreamList):
    """Validate that streams exist and are properly instantiated as StreamList."""

    for stream in streams:
        assert isinstance(stream, Stream)
        assert stream.id is not None
        assert str(stream.url).startswith("https://")


# Audio streams validation
async def test_audio_streams_validation(streams: StreamList):
    """
    Validate properties specific to AudioStream objects.
    (e.g., format_id 139, 140, 249, 251).
    """

    audios = streams.audio_only()
    assert len(audios) > 0, "No audio-only streams were parsed."

    for audio in audios:
        assert audio.type == "audio"
        assert audio.audio is not None
        assert audio.audio.codec != "none"

        if audio.audio.bitrate:
            assert audio.quality == audio.audio.bitrate
        else:
            assert audio.quality == 0

    # Specific check against known audio format from data
    itag_140 = next((s for s in audios if s.id == "140"), None)
    if itag_140:
        assert isinstance(itag_140, AudioStream)
        assert itag_140.audio.codec == "mp4a.40.2"
        assert itag_140.size_type == "exact"
        assert itag_140.size_bytes == 3449447


# VIDEO STREAMS VALIDATION
async def test_video_streams_validation(streams: StreamList):
    """
    Validate properties specific to VideoStream objects.
    (e.g., format_id 160, 133, 134, etc).
    """

    videos = streams.video_only()
    assert len(videos) > 0, "No standard video-only streams were parsed."

    for video in videos:
        assert video.type == "video"
        assert video.video is not None
        assert video.video.codec != "none"
        assert video.video.resolution is not None

        # Check calculated quality properties
        expected_height = video.video.resolution.height
        assert video.quality == expected_height
        assert video.display_quality == f"{expected_height}p"

    # Specific check against known video format from your JSON (itag 135 -> 480p)
    itag_135 = next((s for s in videos if s.id == "135"), None)
    if itag_135:
        assert isinstance(itag_135, VideoStream)
        assert itag_135.video.codec == "avc1.4d401e"
        assert itag_135.quality == 480
        assert itag_135.display_quality == "480p"


# MUXED STREAMS VALIDATION
async def test_muxed_streams_validation(streams: StreamList):
    """
    Validate properties specific to MuxedStream.
    (Video + Audio combined, e.g., format_id 18).
    """

    muxeds = streams.muxed()

    # Format 18 in your JSON is a muxed 360p mp4 stream
    assert len(muxeds) > 0, "No muxed (audio+video) streams were parsed."

    for muxed in muxeds:
        assert muxed.type == "muxed"
        assert muxed.video is not None and muxed.video.codec != "none"
        assert muxed.audio is not None and muxed.audio.codec != "none"

        # MuxedStream inherits quality from VideoStream
        if muxed.video.resolution:
            expected_height = muxed.video.resolution.height
            assert muxed.quality == expected_height
            assert muxed.display_quality == f"{expected_height}p"

    # Specific check against known muxed format from your JSON (itag 18)
    itag_18 = next((s for s in muxeds if s.id == "18"), None)
    if itag_18:
        assert itag_18.video.codec == "avc1.42001E"
        assert itag_18.audio.codec == "mp4a.40.2"
        assert itag_18.display_quality == "360p"


# EDGE CASES & SIZE TYPE INFERENCE
async def test_stream_size_type_mapping(streams: StreamList):
    """
    Validate that `size_type` is correctly inferred.
    The compare is based on `filesize` vs `filesize_approx`.
    """

    for stream in streams:
        if stream.size_bytes is None:
            assert stream.size_type == "unknown"
        elif stream.id == "139":
            assert stream.size_type == "exact"
            assert stream.size_bytes == 1300631
        elif stream.id == "18":
            assert stream.size_type == "estimated"
            assert stream.size_bytes == 11832459
