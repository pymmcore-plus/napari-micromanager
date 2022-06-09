"""Metadata class for managing MDAs."""
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
    """Metadata associated with an MDA sequence.

    TODO: much of this may well move to useq-schema.
    """

    mode: Union[Literal["mda"], Literal["explorer"], Literal[""]] = ""
    split_channels: bool = False
    should_save: bool = False
    file_name: str = ""
    save_dir: str = ""
    save_pos: bool = False


SEQUENCE_META: dict[MDASequence, SequenceMeta] = {}
