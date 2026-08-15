from remora.models.container.extension.audio import (
    AudioContainer,
    AudioContainerLike,
    SafeAudioContainer,
)
from remora.models.container.extension.video import (
    SafeVideoContainer,
    VideoContainer,
    VideoContainerLike,
)

StreamContainer = VideoContainer | AudioContainer
StreamContainerLike = VideoContainerLike | AudioContainerLike
"""Collection of video and audio extension formats."""
SafeContainer = SafeVideoContainer | SafeAudioContainer


def get_stream_container(container: StreamContainerLike | str) -> StreamContainer:
    """Get extension enum from a string."""
    if isinstance(container, StreamContainer):
        return container

    try:
        return VideoContainer(container)
    except ValueError:
        return AudioContainer(container)
