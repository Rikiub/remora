from typing import get_args

from remora.models.container.extension.audio import (
    AudioExtension,
    _AudioExtensionLiteral,
)
from remora.models.container.extension.video import (
    VideoExtension,
    _VideoExtensionLiteral,
)


def test_audio_extension_match_enum():
    """`AudioExtensionStr` must stay in sync with the `AudioExtension` members."""
    assert set(get_args(_AudioExtensionLiteral)) == {e for e in AudioExtension}


def test_video_extension_match_enum():
    """`VideoExtensionStr` must stay in sync with the `VideoExtension` members."""
    assert set(get_args(_VideoExtensionLiteral)) == {e for e in VideoExtension}
