import datetime
from typing import Iterator, Sequence, Union

from pydantic.dataclasses import dataclass
from pydantic.datetime_parse import parse_duration
from pydantic.types import PositiveInt


class timedelta(datetime.timedelta):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, dict):
            return datetime.timedelta(**v)
        return parse_duration(v)


class TimePlan:
    prioritize_duration: bool = False  # or prioritize num frames

    def __iter__(self) -> Iterator[int]:
        for td in self.deltas():
            yield int(1000 * td.total_seconds())

    def __len__(self) -> int:
        return len(list(self.deltas()))

    def deltas(self) -> Iterator[datetime.timedelta]:
        current = timedelta(0)
        for _ in range(self.loops):  # type: ignore  # TODO
            yield current
            current += self.interval  # type: ignore  # TODO

    def __bool__(self) -> bool:
        return len(self) > 0


@dataclass
class TIntervalLoops(TimePlan):
    interval: timedelta
    loops: PositiveInt


@dataclass
class TDurationLoops(TimePlan):
    duration: timedelta
    loops: PositiveInt

    @property
    def interval(self) -> datetime.timedelta:
        # -1 makes it so that the last loop will *occur* at duration, not *finish*
        return self.duration / (self.loops - 1)


@dataclass
class TIntervalDuration(TimePlan):
    interval: timedelta
    duration: timedelta
    prioritize_duration: bool = True

    @property
    def loops(self) -> int:
        return self.duration // self.interval + 1


@dataclass
class NoT(TimePlan):
    """Don't acquire T."""

    def deltas(self):
        yield from ()


SinglePhaseTimePlan = Union[TIntervalDuration, TIntervalLoops, TDurationLoops, NoT]


@dataclass
class MultiPhaseTimePlan(TimePlan):
    phases: Sequence[SinglePhaseTimePlan]

    def deltas(self) -> Iterator[datetime.timedelta]:
        accum = datetime.timedelta(0)
        yield accum
        for phase in self.phases:
            for i, td in enumerate(phase.deltas()):
                # skip the first timepoint of later phases
                if i == 0 and td == datetime.timedelta(0):
                    continue
                yield td + accum
            accum += td


AnyTimePlan = Union[SinglePhaseTimePlan, MultiPhaseTimePlan]
