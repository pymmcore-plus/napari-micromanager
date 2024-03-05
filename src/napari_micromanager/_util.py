from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    import useq

# key in MDASequence.metadata to store napari-micromanager metadata
# note that this is also used in napari layer metadata
NMM_METADATA_KEY = "napari_micromanager"
try:
    from pymmcore_widgets.useq_widgets import PYMMCW_METADATA_KEY as PYMMCW_METADATA_KEY
except ImportError:
    # key in MDASequence.metadata where we expect to find pymmcore_widgets metadata
    PYMMCW_METADATA_KEY = "pymmcore_widgets"

try:
    from pymmcore_plus.mda.handlers._util import (
        get_full_sequence_axes as get_full_sequence_axes,
    )
except ImportError:

    def get_full_sequence_axes(sequence: useq.MDASequence) -> tuple[str, ...]:
        """Get the combined axes from sequence and sub-sequences."""
        # axes main sequence
        main_seq_axes = list(sequence.used_axes)
        if not sequence.stage_positions:
            return tuple(main_seq_axes)
        # axes from sub sequences
        sub_seq_axes: list = []
        for p in sequence.stage_positions:
            if p.sequence is not None:
                sub_seq_axes.extend(
                    [ax for ax in p.sequence.used_axes if ax not in main_seq_axes]
                )
        return tuple(main_seq_axes + sub_seq_axes)


def ensure_unique(path: Path, extension: str = ".tif", ndigits: int = 3) -> Path:
    """Get next suitable filepath (extension = ".tif") or folderpath (extension = "").

    Result is appended with a counter of ndigits.
    """
    p = path
    stem = p.stem
    # check if provided path already has an ndigit number in it
    cur_num = stem.rsplit("_")[-1]
    if cur_num.isdigit() and len(cur_num) == ndigits:
        stem = stem[: -ndigits - 1]
        current_max = int(cur_num) - 1
    else:
        current_max = -1

    # # find the highest existing path (if dir)
    paths = (
        p.parent.glob(f"*{extension}")
        if extension
        else (f for f in p.parent.iterdir() if f.is_dir())
    )
    for fn in paths:
        try:
            current_max = max(current_max, int(fn.stem.rsplit("_")[-1]))
        except ValueError:
            continue

    # build new path name
    number = f"_{current_max+1:0{ndigits}d}"
    return path.parent / f"{stem}{number}{extension}"
