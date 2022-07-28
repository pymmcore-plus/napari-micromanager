from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, Optional

from pymmcore_plus import CMMCorePlus

if TYPE_CHECKING:
    import useq

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


# move these to useq:
def event_indices(event: useq.MDAEvent) -> Iterator[str]:
    """Yield ordered axis names in an event."""
    for k in event.sequence.axis_order if event.sequence else []:
        if k in event.index:
            yield k


def update_pixel_size(
    pixel_size: float,
    obj_dev_label: Optional[str] = None,
    mmc: Optional[CMMCorePlus] = None,
):
    """Update the pixel size config for objective device `obj_dev_label`.

    Parameters
    ----------
    pixel_size : float
        The camera physical pixel size in microns.
    obj_dev_label : Optional[str]
        Device label of the objective to update.  If not provided, will use the
        current `objective_device` label from `CoreState`.`
    mmc : Optional[CMMCorePlus]
        optional mmcore object, by default `CMMCorePlus.instance()`
    """
    if pixel_size == 1.0:
        # TODO: this was previous behavior, but does this make sense?
        # presumably it was here because the default value of the spinbox is 1.0?
        return

    mmc = mmc or CMMCorePlus.instance()
    # if pixel size is already set, and we're not providing a new value, return.
    if current_px_size_cfg := mmc.getCurrentPixelSizeConfig():
        if not pixel_size:
            return
        mmc.deletePixelSizeConfig(current_px_size_cfg)

    # create and store a new pixel size config for the current objective.
    if not obj_dev_label:
        return
    curr_obj = mmc.getProperty(obj_dev_label, "Label")

    # get magnification info from the current objective label
    if match := MAG_PATTERN.search(curr_obj):
        mag = int(match.groups()[0])

        # set image pixel sixe (x,y) for the newly created pixel size config
        resolutionID = f"{RESOLUTION_ID_PREFIX}{curr_obj}"
        mmc.definePixelSizeConfig(resolutionID, obj_dev_label, "Label", curr_obj)
        mmc.setPixelSizeUm(resolutionID, pixel_size / mag)
        mmc.setPixelSizeConfig(resolutionID)
