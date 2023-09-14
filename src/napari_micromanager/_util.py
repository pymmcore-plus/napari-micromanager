from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from useq import MDASequence


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


def get_axis_labels(sequence: MDASequence) -> list[str]:
    """Get the MDASequence axis labels using only axes that are present in events."""
    # axis main sequence
    main_seq_axis = list(sequence.used_axes)
    if not sequence.stage_positions:
        return main_seq_axis
    # axes from sub sequences
    sub_seq_axis: list = []
    for p in sequence.stage_positions:
        if p.sequence is not None:
            sub_seq_axis.extend(
                [ax for ax in p.sequence.used_axes if ax not in main_seq_axis]
            )
    return main_seq_axis + sub_seq_axis
