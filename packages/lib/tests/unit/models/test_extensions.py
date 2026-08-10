from typing import get_args

from remora.models.container import (
    AudioExtension,
    SafeAudioExtensionStr,
    SafeVideoExtensionStr,
    VideoExtension,
)
from remora.models.container.extension.audio import AudioExtensionStr
from remora.models.container.extension.video import VideoExtensionStr


def test_audio_extension_match_enum():
    """`AudioExtensionStr` must stay in sync with the `AudioExtension` members."""
    assert set(get_args(AudioExtensionStr)) == {e for e in AudioExtension}


def test_safe_audio_extension_match_enum():
    """`SafeAudioExtensionStr` must stay in sync with the safe members."""
    assert set(get_args(SafeAudioExtensionStr)) == {
        e.value for e in AudioExtension if e.is_safe
    }


def test_video_extension_match_enum():
    """`VideoExtensionStr` must stay in sync with the `VideoExtension` members."""
    assert set(get_args(VideoExtensionStr)) == {e for e in VideoExtension}


def test_safe_video_extension_match_enum():
    """`SafeVideoExtensionStr` must stay in sync with the safe members."""
    assert set(get_args(SafeVideoExtensionStr)) == {
        e.value for e in VideoExtension if e.is_safe
    }
