from typing import Generic, Self, TypeVar, overload

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    RootModel,
    ValidationError,
    WrapValidator,
    model_validator,
)

from remora._internal.ydl.types import YDLExtractInfo

T = TypeVar("T")


class RemoraBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class YDLSerializable(RemoraBaseModel):
    def to_ydl_dict(self) -> YDLExtractInfo:
        return self.model_dump(by_alias=True, mode="json")

    @model_validator(mode="before")
    @classmethod
    def _validate_ydl(cls, data):
        if isinstance(data, dict) and (
            data.get("extractor_key") or data.get("ie_key") or data.get("format_id")
        ):
            return cls._transform_ydl_dict(data)
        return data

    @classmethod
    def _transform_ydl_dict(cls, info: YDLExtractInfo) -> YDLExtractInfo:
        return info


class BaseList(RootModel[list[T]], Generic[T]):
    root: list[T] = []

    def __contains__(self, other) -> bool:
        return other in self.root

    def __len__(self) -> int:
        return len(self.root)

    def __bool__(self) -> bool:
        return bool(self.root)

    def __iter__(self):  # type: ignore
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
