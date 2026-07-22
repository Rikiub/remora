import pytest

from remora._internal.extractor import MediaExtractor
from remora.exceptions import ExtractorError


@pytest.mark.parametrize(
    "url",
    [
        "https://unkdown.link.com/",  # Invalid URL
        "https://www.youtube.com/watch?v=yi50KlsCBio",  # Private video
        "https://www.youtube.com/watch?v=JUf1zxjR_Qw",  # Deleted video
    ],
)
async def test_exceptions(extractor: MediaExtractor, url: str):
    with pytest.raises(ExtractorError):
        await extractor.extract(url)
