import textwrap

import pytest

from remora.models.metadata.size import Resolution
from remora.models.metadata.thumbnail import (
    Thumbnail,
    ThumbnailList,
)


@pytest.fixture
def thumbnails() -> ThumbnailList:
    URL = "https://example.com/thumbnail"

    return ThumbnailList(
        [
            Thumbnail(
                id="4",
                url=URL,
                priority=-3,
            ),
            Thumbnail(
                id="1",
                url=URL,
                resolution=Resolution(width=500, height=500),
                priority=-1,
            ),
            Thumbnail(
                id="3",
                url=URL,
                resolution=Resolution(width=300, height=300),
                priority=-2,
            ),
            Thumbnail(
                id="2",
                url=URL,
                # By default the priority is 0
            ),
        ]
    )


async def test_sort_best(thumbnails: ThumbnailList):
    sorted = thumbnails.sorted_by("best")

    expected_ids = ["2", "1", "3", "4"]  # Must match with the IDs in the fixture
    thumb_ids = [t.id for t in sorted]
    assert len(thumb_ids) > 0

    for index, _ in enumerate(thumb_ids):
        assert expected_ids[index] == thumb_ids[index], textwrap.dedent(
            f"""The sort order don't match.
            The list was sorted as: {thumb_ids}
            But should be: {expected_ids}
            """
        )
