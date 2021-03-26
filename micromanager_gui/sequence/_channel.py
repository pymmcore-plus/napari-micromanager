from typing import Optional

from pydantic import BaseModel
from pydantic.types import PositiveFloat, PositiveInt


class Channel(BaseModel):
    config: str
    group: str = "Channel"
    exposure: Optional[PositiveFloat] = None
    do_stack: bool = True
    z_offset: float = 0.0
    acquire_every: PositiveInt = 1  # acquire every n frames
    camera: Optional[str] = None

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        if isinstance(value, Channel):
            return value
        if isinstance(value, str):
            return Channel(config=value)
        if isinstance(value, dict):
            return Channel(**value)
