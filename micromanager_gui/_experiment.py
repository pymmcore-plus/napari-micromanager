from dataclasses import dataclass, field
from typing import Iterator, Tuple

import numpy as np


@dataclass(frozen=True)
class MDASequence:
    acquisition_order: str = "tpcz"
    # tuples of (channel_name, exposure time)
    channels: Tuple[Tuple[str, int], ...] = field(default_factory=tuple)
    stage_positions: Tuple[Tuple[float, float, float], ...] = field(
        default_factory=tuple
    )
    time_deltas: Tuple[int, ...] = field(default_factory=tuple)
    z_positions: Tuple[float, ...] = field(default_factory=tuple)

    def __str__(self):
        out = "Multi-Dimensional Acquisition ▶ "
        shape = [
            f"n{k.upper()}: {len(self._axes_dict[k])}" for k in self.acquisition_order
        ]
        out += ", ".join(shape)
        return out

    def __len__(self):
        return np.prod(self.shape)

    @property
    def shape(self) -> Tuple[int, ...]:
        return tuple(len(self._axes_dict[k]) for k in self.acquisition_order)

    @property
    def _axes_dict(self):
        return {
            "c": self.channels,
            "z": self.z_positions,
            "p": self.stage_positions,
            "t": self.time_deltas,
        }

    def __iter__(self) -> Iterator["Frame"]:
        yield from self.iter_axes(self.acquisition_order)

    def iter_axes(self, order: str = None) -> Iterator["Frame"]:
        from itertools import product

        order = order if order else self.acquisition_order
        order = order.lower()
        extra = {x for x in order if x not in "tpcz"}
        if extra:
            raise ValueError(
                f"Can only iterate over axes: t, p, z, c.  Got extra: {extra}"
            )
        if len(set(order)) < len(order):
            raise ValueError(f"Duplicate entries found in acquisition order: {order}")

        for item in product(*(self._axes_dict[ax] for ax in order)):
            yield Frame(**dict(zip(order, item)), exp=self)


@dataclass(frozen=True)
class Frame:
    t: int  # (desired) msec from start of experiment
    c: Tuple[str, int]  # tuple of channel name, exposure time
    z: float  # z positions (around middle)
    p: Tuple[float, float, float]  # middle stage position (x,y,z)
    exp: MDASequence

    def __str__(self):
        ch, exp = self.c
        x, y, z = self.p
        z += self.z
        return f"t{self.t}, pos<{x}, {y}, {z}>, channel {ch} {exp}ms"
