import pytest

from remora.models.options.download import DownloadOptions


def test_output_template():
    with pytest.raises(ValueError):
        DownloadOptions(output_template="{wrong_key}")


def test_ffmpeg():
    with pytest.raises(ValueError):
        DownloadOptions(ffmpeg_location="/invalid_dir/")


def test_format():
    DownloadOptions(convert_to="mp3")
    DownloadOptions(convert_to="mka")
