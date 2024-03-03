"""Metadata class for managing MDAs."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace as _replace
from typing import Any

__all__ = ["SequenceMeta", "SEQUENCE_META_KEY"]


# This is the key in the MDASequence.metadata dict that will contain the
# SequenceMeta object.
SEQUENCE_META_KEY = "napari_mm_sequence_meta"


# Should we simply use a dict now that we onky have two keys in here?
@dataclass(frozen=True)
class SequenceMeta:
    """Metadata associated with an MDA sequence."""

    mode: str = ""
    split_channels: bool = False

    def replace(self, **kwargs: Any) -> SequenceMeta:
        """Return a new SequenceMeta with the given kwargs replaced."""
        return _replace(self, **kwargs)
