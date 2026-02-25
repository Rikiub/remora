from remora.models.format.audio import (
    AudioExtension,
    AudioExtensionType,
    SafeAudioExtensionStr,
)
from remora.models.format.type import FormatKindStr
from remora.models.format.video import (
    SafeVideoExtensionStr,
    VideoExtension,
    VideoExtensionType,
)

ExtensionType = VideoExtensionType | AudioExtensionType
FormatTargetStr = FormatKindStr | SafeAudioExtensionStr | SafeVideoExtensionStr


def get_extension(
    extension: str | ExtensionType,
) -> VideoExtension | AudioExtension:
    try:
        return VideoExtension(extension)
    except ValueError:
        return AudioExtension(extension)
