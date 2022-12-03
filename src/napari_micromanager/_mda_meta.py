"""Metadata class for managing MDAs."""
from __future__ import annotations

from dataclasses import dataclass, field

from useq import MDASequence

__all__ = [
    "SequenceMeta",
    "SEQUENCE_META",
]


@dataclass
class SequenceMeta:
    """Metadata associated with an MDA sequence."""

    mode: str = ""
    split_channels: bool = False
    should_save: bool = False
    file_name: str = ""
    save_dir: str = ""
    save_pos: bool = False
    translate_explorer: bool = False
    explorer_translation_points: list = field(default_factory=list)
    scan_size_r: int = 0
    scan_size_c: int = 0


SEQUENCE_META: dict[MDASequence, SequenceMeta] = {}
