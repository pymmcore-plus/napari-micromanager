"""Metadata class for managing MDAs."""
from __future__ import annotations

from dataclasses import dataclass
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
    file_name: str = ""
    save_dir: str = ""
    should_save: bool = False  # to remove when using pymmcore-plus writers
    save_pos: bool = False  # to remove when using pymmcore-plus writers

    def replace(self, **kwargs: Any) -> SequenceMeta:
        """Return a new SequenceMeta with the given kwargs replaced."""
        return _replace(self, **kwargs)
