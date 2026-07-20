from typing import Annotated

from pydantic import AfterValidator, Field, HttpUrl

from remora.models.metadata._base import Metadata


def _clean_uploader_name(v: str) -> str:
    if not v:
        return ""
    return v.split(",")[0].removesuffix(" - Topic")


class Uploader(Metadata):
    name: Annotated[
        str,
        AfterValidator(_clean_uploader_name),
        Field(alias="uploader"),
    ]
    id: Annotated[str | None, Field(alias="uploader_id")] = None
    url: Annotated[HttpUrl | None, Field(alias="uploader_url")] = None


class Channel(Metadata):
    name: Annotated[str, Field(alias="channel")]
    id: Annotated[str | None, Field(alias="channel_id")] = None
    url: Annotated[HttpUrl | None, Field(alias="channel_url")] = None
    is_verified: Annotated[bool | None, Field(alias="channel_is_verified")] = None
    followers: Annotated[int | None, Field(alias="channel_follower_count")] = None


class Metrics(Metadata):
    views: Annotated[int | None, Field(alias="view_count")] = None
    viewers: Annotated[int | None, Field(alias="concurrent_view_count")] = None

    likes: Annotated[int | None, Field(alias="like_count")] = None
    dislikes: Annotated[int | None, Field(alias="dislike_count")] = None
    comments: Annotated[int | None, Field(alias="comment_count")] = None

    reposts: Annotated[int | None, Field(alias="repost_count")] = None
    saves: Annotated[int | None, Field(alias="save_count")] = None
