from typing import get_args

from remora.models.container import (
    AudioExtension,
    SafeAudioExtension,
    SafeVideoExtension,
    VideoExtension,
)
from remora.models.container.extension.audio import _AudioExtensionLiteral
from remora.models.container.extension.video import _VideoExtensionLiteral


def test_audio_extension_match_enum():
    """`AudioExtensionStr` must stay in sync with the `AudioExtension` members."""
    assert set(get_args(_AudioExtensionLiteral)) == {e for e in AudioExtension}


def test_safe_audio_extension_match_enum():
    """`SafeAudioExtensionStr` must stay in sync with the safe members."""
    assert set(get_args(SafeAudioExtension)) == {
        e.value for e in AudioExtension if e.is_safe
    }


def test_video_extension_match_enum():
    """`VideoExtensionStr` must stay in sync with the `VideoExtension` members."""
    assert set(get_args(_VideoExtensionLiteral)) == {e for e in VideoExtension}


def test_safe_video_extension_match_enum():
    """`SafeVideoExtensionStr` must stay in sync with the safe members."""
    assert set(get_args(SafeVideoExtension)) == {
        e.value for e in VideoExtension if e.is_safe
    }
