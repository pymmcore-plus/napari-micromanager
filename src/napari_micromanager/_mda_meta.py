"""Metadata class for managing MDAs."""
from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import replace as _replace
from typing import Any

__all__ = ["SequenceMeta", "SEQUENCE_META_KEY"]


# This is the key in the MDASequence.metadata dict that will contain the
# SequenceMeta object.
SEQUENCE_META_KEY = "napari_mm_sequence_meta"


@dataclass(frozen=True)
class SequenceMeta:
    """Metadata associated with an MDA sequence."""

    mode: str = ""
    split_channels: bool = False
    should_save: bool = False
    file_name: str = ""
    save_dir: str = ""
    save_pos: bool = False
    translate_explorer: bool = False
    # [(x, y, r, c), ...] for each row in the scan
    explorer_translation_points: list[tuple[float, float, int, int]] = field(
        default_factory=list
    )
    scan_size_r: int = 0
    scan_size_c: int = 0

    def replace(self, **kwargs: Any) -> SequenceMeta:
        """Return a new SequenceMeta with the given kwargs replaced."""
        return _replace(self, **kwargs)
