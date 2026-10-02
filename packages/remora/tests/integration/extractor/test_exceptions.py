import pytest

from remora import Client
from remora.exceptions import ExtractorError


@pytest.mark.parametrize(
    "url",
    [
        "https://unkdown.link.com/",  # Invalid URL
        "https://www.youtube.com/watch?v=yi50KlsCBio",  # Private video
        "https://www.youtube.com/watch?v=JUf1zxjR_Qw",  # Deleted video
    ],
)
async def test_exceptions(client: Client, url: str):
    with pytest.raises(ExtractorError):
        await client.extract(url)
