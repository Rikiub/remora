import pytest

from remora.models.media.item import Media
from remora.models.metadata.thumbnail import ThumbnailList


@pytest.fixture
def thumb(ydl_data):
    data = ydl_data("youtube/video.json")
    data = Media(**data)

    assert len(data.thumbnails) > 1
    return data.thumbnails


async def test_sort_best(thumb: ThumbnailList):
    thumb = thumb.sorted_by("best")

    for i in range(len(thumb) - 1):
        current = thumb[i]
        next = thumb[i + 1]
        assert current.extractor_meta.preference >= next.extractor_meta.preference
