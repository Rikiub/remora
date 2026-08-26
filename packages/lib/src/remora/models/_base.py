import functools
from collections.abc import Iterator, Sequence
from typing import Generic, Self, TypeVar, overload

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    RootModel,
    ValidationError,
    WrapValidator,
)

from remora._internal.ydl.types import YDLExtractInfo


class RemoraModel(BaseModel):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)


class YDLSerializable(RemoraModel):
    def _to_ydl_dict(self) -> YDLExtractInfo:
        return self.model_dump(by_alias=True, mode="json")


Impersonate = bool | list[str]

_T = TypeVar("_T")


class BaseList(RootModel[Sequence], Sequence[_T], Generic[_T]):
    root: list[_T] = []

    def __contains__(self, other) -> bool:
        return other in self.root

    def __len__(self) -> int:
        return len(self.root)

    def __bool__(self) -> bool:
        return bool(self.root)

    def __iter__(self) -> Iterator[_T]:  # type: ignore
        return iter(self.root)

    @overload
    def __getitem__(self, index: int) -> _T: ...

    @overload
    def __getitem__(self, index: slice) -> Self: ...

    def __getitem__(self, index: int | slice) -> _T | Self:
        if isinstance(index, slice):
            return self.__class__(self.root[index])
        elif isinstance(index, int):
            return self.root[index]
        else:
            raise TypeError(f"Invalid argument type: {type(index)}")


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


def rgetattr(obj: object, attr: str, *args) -> object | None:
    """Get attribute recursively."""

    def _getattr(obj, attr):
        return getattr(obj, attr, *args)

    return functools.reduce(_getattr, attr.split("."), obj)
