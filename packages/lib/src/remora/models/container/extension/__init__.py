from remora.models.container.extension.audio import (
    AudioExtension,
    AudioExtensionType,
    SafeAudioExtensionStr,  # noqa: F401
)
from remora.models.container.extension.video import (
    SafeVideoExtensionStr,  # noqa: F401
    VideoExtension,
    VideoExtensionType,
)

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
