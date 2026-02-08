from typing import Literal

from pydantic import BaseModel


class State(BaseModel):
    id: str


class HasFile(State):
    extension: str


StageType = Literal["started", "completed"]
