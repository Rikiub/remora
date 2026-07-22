import pytest

from remora.models.media.item import Media
from remora.models.stream.item import AudioStream, MuxedStream, VideoStream
from remora.models.stream.list import StreamList
from remora.models.stream.type import StreamKind


@pytest.fixture
async def media(extract_ydl) -> Media:
    data = await extract_ydl("youtube/video.json")
    assert isinstance(data, Media)
    return data


# GENERAL STREAM LIST VALIDATION
async def test_media_streams_presence_and_types(media: Media):
    """Validate that streams exist and are properly instantiated as StreamList."""
    assert isinstance(media.streams, StreamList)
    assert len(media.streams) > 0

    # Every parsed item in the list must match one of our discriminated Pydantic models
    for stream in media.streams:
        assert isinstance(stream, (AudioStream, VideoStream, MuxedStream))
        assert stream.id is not None
        assert str(stream.url).startswith("https://")


async def test_stream_list_sorting_order(media: Media):
    """
    Validate that the AfterValidator(lambda list: list.sorted_by('best'))
    successfully orders the streams from best quality to lowest quality.
    """

    streams = media.streams
    if len(streams) < 2:
        pytest.skip("Not enough streams to test sorting.")

    # Validate that quality generally trends downward or stays equal
    # (Assuming 'best' sorts by quality descending)
    for i in range(len(streams) - 1):
        current_stream = streams[i]
        next_stream = streams[i + 1]

        # We check that the current item's quality >= next item's quality
        # Note: If sorted_by('best') separates audio and video, you may need to
        # filter by isinstance first before comparing numerical qualities.
        if type(current_stream) is type(next_stream):
            assert current_stream.quality >= next_stream.quality, (
                f"Stream sorting failed: format_id {current_stream.id} "
                f"({current_stream.quality}) is placed before {next_stream.id} "
                f"({next_stream.quality})"
            )


# AUDIO STREAMS VALIDATION
async def test_audio_streams_validation(media: Media):
    """Validate properties specific to AudioStream objects (e.g., format_id 139, 140, 249, 251)."""

    audio_streams = [
        s
        for s in media.streams
        if isinstance(s, AudioStream) and not isinstance(s, MuxedStream)
    ]
    assert len(audio_streams) > 0, "No audio-only streams were parsed."

    for audio in audio_streams:
        assert audio.type == StreamKind.AUDIO
        assert audio.audio is not None
        assert audio.audio.codec != "none"

        # Check calculated quality properties
        if audio.audio.bitrate:
            assert audio.quality == audio.audio.bitrate
            assert audio.display_quality == f"{round(audio.audio.bitrate)}kbps"
        else:
            assert audio.quality == 0
            assert audio.display_quality == "0kbps"

    # Specific check against known audio format from your JSON (itag 140)
    itag_140 = next((s for s in audio_streams if s.id == "140"), None)
    if itag_140:
        assert isinstance(itag_140, AudioStream)
        assert itag_140.audio.codec == "mp4a.40.2"
        assert itag_140.size_type == "exact"
        assert itag_140.size_bytes == 3449447


# VIDEO STREAMS VALIDATION
async def test_video_streams_validation(media: Media):
    """Validate properties specific to VideoStream objects (e.g., format_id 160, 133, 134, etc)."""
    video_streams = [
        s
        for s in media.streams
        if isinstance(s, VideoStream)
        and not isinstance(s, MuxedStream)
        # Exclude storyboards (sb0, sb1...) if they parsed as VideoStreams
        and not s.id.startswith("sb")
    ]
    assert len(video_streams) > 0, "No standard video-only streams were parsed."

    for video in video_streams:
        assert video.type == StreamKind.VIDEO
        assert video.video is not None
        assert video.video.codec != "none"
        assert video.video.resolution is not None

        # Check calculated quality properties
        expected_height = video.video.resolution.height
        assert video.quality == expected_height
        assert video.display_quality == f"{expected_height}p"

    # Specific check against known video format from your JSON (itag 135 -> 480p)
    itag_135 = next((s for s in video_streams if s.id == "135"), None)
    if itag_135:
        assert isinstance(itag_135, VideoStream)
        assert itag_135.video.codec == "avc1.4d401e"
        assert itag_135.quality == 480
        assert itag_135.display_quality == "480p"


# MUXED STREAMS VALIDATION
async def test_muxed_streams_validation(media: Media):
    """Validate properties specific to MuxedStream (Video + Audio combined, e.g., format_id 18)."""

    muxed_streams = [s for s in media.streams if isinstance(s, MuxedStream)]

    # Format 18 in your JSON is a muxed 360p mp4 stream
    assert len(muxed_streams) > 0, "No muxed (audio+video) streams were parsed."

    for muxed in muxed_streams:
        assert muxed.type == StreamKind.MUXED
        assert muxed.video is not None and muxed.video.codec != "none"
        assert muxed.audio is not None and muxed.audio.codec != "none"

        # MuxedStream inherits quality from VideoStream
        if muxed.video.resolution:
            expected_height = muxed.video.resolution.height
            assert muxed.quality == expected_height
            assert muxed.display_quality == f"{expected_height}p"

    # Specific check against known muxed format from your JSON (itag 18)
    itag_18 = next((s for s in muxed_streams if s.id == "18"), None)
    if itag_18:
        assert itag_18.video.codec == "avc1.42001E"
        assert itag_18.audio.codec == "mp4a.40.2"
        assert itag_18.display_quality == "360p"


# EDGE CASES & SIZE TYPE INFERENCE
async def test_stream_size_type_mapping(media: Media):
    """Validate that size_type is correctly inferred based on filesize vs filesize_approx."""

    for stream in media.streams:
        if stream.size_bytes is None:
            assert stream.size_type == "unknown"
        elif stream.id == "139":
            assert stream.size_type == "exact"
            assert stream.size_bytes == 1300631
        elif stream.id == "18":
            assert stream.size_type == "estimated"
            assert stream.size_bytes == 11832459
