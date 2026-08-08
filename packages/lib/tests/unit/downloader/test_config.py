import pytest

from remora.exceptions import FFmpegNotFoundError
from remora.models.download_options import DownloadOptions


def test_output_template():
    with pytest.raises(ValueError):
        DownloadOptions(output_template="{wrong_key}")


def test_ffmpeg():
    with pytest.raises(FFmpegNotFoundError):
        DownloadOptions(ffmpeg_path="{wrong_key}")


def test_format():
    DownloadOptions(convert_to="mp3")
    DownloadOptions(convert_to="mka")
