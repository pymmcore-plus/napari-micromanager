from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from pymmcore_plus import CMMCorePlus

if TYPE_CHECKING:
    pass

MAG_PATTERN = re.compile(r"(\d{1,3})[xX]")
RESOLUTION_ID_PREFIX = "px_size_"


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


def iter_dev_props(mmc: CMMCorePlus | None = None) -> Iterator[tuple[str, str]]:
    """Yield all pairs of currently loaded (device_label, property_name)."""
    mmc = mmc or CMMCorePlus.instance()
    for dev in mmc.getLoadedDevices():
        for prop in mmc.getDevicePropertyNames(dev):
            yield dev, prop