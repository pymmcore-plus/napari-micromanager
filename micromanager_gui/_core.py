"""Functions and utils for managing the global mmcore singleton."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar, Optional

from pymmcore_plus import CMMCorePlus

MAG_PATTERN = re.compile(r"(\d{1,3})[xX]")
RESOLUTION_ID_PREFIX = "px_size_"
_SESSION_CORE = None


def get_core_singleton(remote=False) -> CMMCorePlus:
    """Retrieve the MMCore singleton for this session.

    The first call to this function determines whether we're running remote or not.
    perhaps a temporary function for now...
    """
    global _SESSION_CORE
    if _SESSION_CORE is None:
        if remote:
            from pymmcore_plus import RemoteMMCore

            _SESSION_CORE = RemoteMMCore()
        else:
            _SESSION_CORE = CMMCorePlus.instance()
    return _SESSION_CORE


@dataclass
class CoreState:
    """An object to store CMMCore related state.

    This is stuff for which pymmcore.CMMCore doesn't provide an API.
    It could all conceivably be put on the global CMMCorePlus.instance() singleton,
    but for now we maintain an independent state object.
    """

    objective_device: Optional[str] = None
    objectives_cfg: Optional[str] = None

    __instance: ClassVar[Optional[CoreState]] = None

    @classmethod
    def instance(cls) -> CoreState:
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance


STATE = CoreState.instance()


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

    mmc = mmc or get_core_singleton()
    # if pixel size is already set, and we're not providing a new value, return.
    if current_px_size_cfg := mmc.getCurrentPixelSizeConfig():
        if not pixel_size:
            return
        mmc.deletePixelSizeConfig(current_px_size_cfg)

    # create and store a new pixel size config for the current objective.
    obj_dev_label = obj_dev_label or STATE.objective_device
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
