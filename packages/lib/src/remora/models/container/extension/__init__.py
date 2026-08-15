from remora.models.container.extension.audio import (
    AudioExtension,
    AudioExtensionLike,
    SafeAudioExtension,
)
from remora.models.container.extension.video import (
    SafeVideoExtension,
    VideoExtension,
    VideoExtensionLike,
)

Extension = VideoExtension | AudioExtension
ExtensionLike = VideoExtensionLike | AudioExtensionLike
"""Collection of video and audio extension formats."""
SafeExtension = SafeVideoExtension | SafeAudioExtension


def get_extension(extension: ExtensionLike | str) -> Extension:
    """Get extension enum from a string."""
    if isinstance(extension, Extension):
        return extension

    try:
        return VideoExtension(extension)
    except ValueError:
        return AudioExtension(extension)
