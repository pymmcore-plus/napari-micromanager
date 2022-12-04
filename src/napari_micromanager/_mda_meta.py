"""Metadata class for managing MDAs."""
from __future__ import annotations

from dataclasses import dataclass, field


__all__ = ["SequenceMeta", "SEQUENCE_META_KEY"]


# This is the key in the MDASequence.metadata dict that will contain the
# SequenceMeta object.
SEQUENCE_META_KEY = "napari_mm_sequence_meta"


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
