from remora._internal.types.audio import AudioExtension, AudioExtensionLike
from remora._internal.types.base import ExtensionType, ExtensionTypeLike
from remora._internal.types.video import VideoExtension, VideoExtensionLike

StreamExtension = VideoExtension | AudioExtension
StreamExtensionLike = VideoExtensionLike | AudioExtensionLike

StreamTarget = ExtensionType | StreamExtension
StreamTargetLike = ExtensionTypeLike | StreamExtensionLike


def get_extension(extension: str) -> VideoExtension | AudioExtension:
    try:
        return VideoExtension(extension)
    except ValueError:
        return AudioExtension(extension)
