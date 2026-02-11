from typing import Generic, TypeVar, overload

from pydantic import BaseModel, RootModel
from remora.ydl.types import YDLExtractInfo
from typing_extensions import Self


class YDLSerializable(BaseModel):
    def to_ydl_dict(self) -> YDLExtractInfo:
        return self.model_dump(by_alias=True, mode="json")

    def to_ydl_json(self) -> str:
        return self.model_dump_json(by_alias=True)

    @classmethod
    def from_ydl_json(cls, data: str) -> Self:
        return cls.model_validate_json(data, by_alias=True)


T = TypeVar("T")


class BaseList(RootModel[list[T]], Generic[T]):
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
