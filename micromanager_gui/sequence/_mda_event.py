from __future__ import annotations

from typing import Any, NamedTuple, Sequence

from pydantic import BaseModel, Field
from pydantic.types import PositiveFloat


class Channel(BaseModel):
    config: str
    group: str = "Channel"


class PropertyTuple(NamedTuple):
    device_name: str
    property_name: str
    property_value: Any


class MDAEvent(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)
    index: dict[str, int] = Field(default_factory=dict)
    channel: Channel | None = None
    exposure: PositiveFloat | None = None
    min_start_time: int | None = None
    x_pos: float | None = None
    y_pos: float | None = None
    z_pos: float | None = None
    properties: Sequence[PropertyTuple] | None = None
    # sequence: Optional["MDASequence"] = None
    # action
    # keep shutter open between channels/steps

    def __repr__(self) -> str:
        return super().__repr__()

    def to_pycromanager(self) -> dict:
        d: dict = {
            "exposure": self.exposure,
            "axes": {},
            "z": self.z_pos,
            "x": self.x_pos,
            "y": self.y_pos,
            "min_start_time": self.min_start_time,
            "channel": self.channel and self.channel.dict(),
        }
        if "p" in self.index:
            d["axes"]["position"] = self.index["p"]
        if "t" in self.index:
            d["axes"]["time"] = self.index["t"]
        if "z" in self.index:
            d["axes"]["z"] = self.index["z"]
        if self.properties:
            d["properties"] = [list(p) for p in self.properties]

        for key, value in list(d.items()):
            if value is None:
                d.pop(key)
        return d
