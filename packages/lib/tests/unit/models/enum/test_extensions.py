def test_audio_extension_match_enum():
    """`AudioExtensionStr` must stay in sync with the `AudioExtension` members."""
    # assert set(get_args(_AudioContainerLiteral)) == {e for e in AudioContainer}


def test_video_extension_match_enum():
    """`VideoExtensionStr` must stay in sync with the `VideoExtension` members."""
    # assert set(get_args(_VideoContainerLiteral)) == {e for e in VideoContainer}
