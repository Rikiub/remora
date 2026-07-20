from remora.models._base import Resolution
from remora.models.format.type import FormatKind
from remora.models.media.item import LiveStatus, Media
from remora.models.metadata.music import MusicMetadata
from remora.models.stream.item import (
    AudioInfo,
    AudioStream,
    MuxedStream,
    Stream,
    VideoInfo,
    VideoStream,
    YDLOptions,
)


class YDLDeserializer:
    @staticmethod
    def media(data: dict) -> Media:
        # Map music
        data["music"] = MusicMetadata(**data)

        # Prepare live status
        live_status: LiveStatus = "not_live"

        is_live = data.get("is_live")
        was_live = data.get("was_live")
        is_upcoming = (
            data.get("live_status") == "is_upcoming"
            or data.get("availability") == "upcoming"
        )

        if is_live:
            live_status = "live"
        elif is_upcoming:
            live_status = "upcoming"
        elif was_live:
            live_status = "was_live"

        data["live_status"] = live_status

        # Prepare Media
        return Media(**data)

    @staticmethod
    def stream(data: dict) -> Stream:
        # Determine format type
        vcodec = data.get("vcodec")
        acodec = data.get("acodec")

        if vcodec and acodec:
            type = FormatKind.MUXED
        elif not acodec and vcodec:
            type = FormatKind.VIDEO
        elif not vcodec and acodec:
            type = FormatKind.AUDIO
        else:
            raise ValueError("Unable to determine stream format")

        # Map common fields
        common = {
            "id": data["format_id"],
            "url": data["url"],
            "protocol": data["protocol"],
            "size_type": data.get("size_type") or "unknown",
            "size_bytes": data.get("filesize") or data.get("filesize_approx"),
            "extension": data.get("ext"),
            "ydl_options": YDLOptions(
                headers=data.pop("http_headers", {}),
                cookies=data.pop("cookies", None),
                extra=data.pop("downloader_options", {}),
            ),
        }

        # Map resolution
        resolution = None
        width = data.get("width")
        height = data.get("height")

        if width and height:
            resolution = Resolution(width=width, height=height)

        # Map info fields
        video_info = {
            **data,
            "codec": data.get("vcodec"),
            "bitrate": data.get("vbr"),
            "resolution": resolution,
        }
        audio_info = {
            **data,
            "codec": data.get("acodec"),
            "bitrate": data.get("abr"),
        }

        match type:
            case FormatKind.MUXED:
                return MuxedStream(
                    **common,
                    video=VideoInfo(**video_info),
                    audio=AudioInfo(**audio_info),
                )
            case FormatKind.VIDEO:
                return VideoStream(
                    **common,
                    video=VideoInfo(**video_info),
                )
            case FormatKind.AUDIO:
                return AudioStream(
                    **common,
                    audio=AudioInfo(**audio_info),
                )
