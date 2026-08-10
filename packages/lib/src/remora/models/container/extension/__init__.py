from remora.models.container.extension.audio import AudioExtension, AudioExtensionType
from remora.models.container.extension.video import VideoExtension, VideoExtensionType

ExtensionType = VideoExtensionType | AudioExtensionType
"""Collection of video and audio extension formats."""


def get_extension(
    extension: str | ExtensionType,
) -> VideoExtension | AudioExtension:
    """Get extension enum from a string."""
    try:
        return VideoExtension(extension)
    except ValueError:
        return AudioExtension(extension)


__all__ = [
    "AudioExtension",
    "AudioExtensionType",
    "ExtensionType",
    "VideoExtension",
    "VideoExtensionType",
    "get_extension",
]
