import functools
from collections.abc import Iterable, Iterator, Sequence
from typing import Any, Generic, Self, TypeVar, overload

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    RootModel,
    ValidationError,
    WrapValidator,
)

from remora._ydl.types import YDLExtractInfo


# Base Models
class RemoraModel(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        validate_by_alias=True,
        frozen=True,
    )


class YDLSerializable(RemoraModel):
    def _to_ydl_dict(self) -> YDLExtractInfo:
        return self.model_dump(by_alias=True, mode="json")


# Specializations
Impersonate = bool | tuple[str, ...]

# BaseList
_T = TypeVar("_T")


class BaseTuple(RootModel[Sequence], Sequence[_T], Generic[_T]):
    root: tuple[_T, ...] = ()

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


# Recursive getattr
_R = TypeVar("_R")


@overload
def rgetattr(obj: Any, attr: str) -> Any: ...


# Overload 2: Called with a default value. Returns either the found type or the default type
@overload
def rgetattr(obj: Any, attr: str, default: _R) -> Any | _R: ...


def rgetattr(obj: Any, attr: str, *args: Any) -> Any:
    """Get attribute recursively."""

    def _getattr(obj, attr):
        return getattr(obj, attr, *args)

    return functools.reduce(_getattr, [obj] + attr.split("."))


# Validators
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

EnsureTuple = BeforeValidator(lambda v: v if v else ())
"""Ensure data will be empty tuple if field not exists."""

EnsureBool = BeforeValidator(lambda v: bool(v))
"""Ensure data will be False if field not exists."""

# Filter Types
_F = TypeVar("_F")
FilterValue = Iterable[_F] | _F | None


def to_tuple(value: _F | Iterable[_F]) -> tuple[_F, ...]:
    """Normalize a string or iterable of strings into a tuple."""
    if isinstance(value, (str, int, bytes)):
        return (value,)  # ty: ignore[invalid-return-type]
    if isinstance(value, Iterable):
        return tuple(value)
    return tuple(value)  # ty: ignore[invalid-argument-type]
