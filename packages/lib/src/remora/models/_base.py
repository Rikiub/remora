from collections.abc import Iterator
from typing import Generic, Self, TypeVar, overload

from pydantic import (
    BaseModel,
    BeforeValidator,
    RootModel,
    ValidationError,
    WrapValidator,
)

from remora._internal.ydl.types import YDLExtractInfo

T = TypeVar("T")


class RemoraBaseModel(BaseModel): ...


class Resolution(RemoraBaseModel):
    width: int
    height: int


class YDLSerializable(RemoraBaseModel):
    def to_ydl_dict(self) -> YDLExtractInfo:
        return self.model_dump(by_alias=True, mode="json")


class BaseList(RootModel[list[T]], Generic[T]):
    root: list[T] = []

    def __contains__(self, other) -> bool:
        return other in self.root

    def __len__(self) -> int:
        return len(self.root)

    def __bool__(self) -> bool:
        return bool(self.root)

    def __iter__(self) -> Iterator[T]:  # type: ignore
        return iter(self.root)

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> Self: ...

    def __getitem__(self, index) -> T | Self:
        match index:
            case int() | slice():
                return self.root[index]  # type: ignore
            case _:
                raise TypeError(index)


def _validate_or_none(v, handler):
    """Models must implement __bool__ to ensure validation."""

    try:
        model = handler(v)

        if model:
            return model
        else:
            return None
    except ValidationError:
        return None


EnsureNone = WrapValidator(_validate_or_none)
"""Ensure data will be None if field not exists."""

EnsureList = BeforeValidator(lambda v: v if v else [])
"""Ensure data will be empty list if field not exists."""
