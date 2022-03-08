"""metadata class and shared state for managing MDAs"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from typing_extensions import Literal
from useq import MDASequence

__all__ = [
    "SequenceMeta",
    "SEQUENCE_META",
]


@dataclass
class SequenceMeta:
    mode: Union[Literal["mda"], Literal["explorer"]] = ""
    split_channels: bool = False
    should_save: bool = False
    file_name: str = ""
    save_dir: str = ""
    save_pos: bool = False


SEQUENCE_META: dict[MDASequence, SequenceMeta] = {}
