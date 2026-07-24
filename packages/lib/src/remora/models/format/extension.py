from remora.models.format.audio import (
    AudioExtension,
    AudioExtensionType,
    SafeAudioExtensionStr,
)
from remora.models.format.format import FormatType
from remora.models.format.video import (
    SafeVideoExtensionStr,
    VideoExtension,
    VideoExtensionType,
)

ExtensionType = VideoExtensionType | AudioExtensionType
"""Collection of video and audio extension formats."""

FormatTargetType = FormatType | SafeAudioExtensionStr | SafeVideoExtensionStr
"""Collection of standard and safe extension formats."""


def get_extension(
    extension: str | ExtensionType,
) -> VideoExtension | AudioExtension:
    """Get extension enum from a string."""
    try:
        return VideoExtension(extension)
    except ValueError:
        return AudioExtension(extension)
