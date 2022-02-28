from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar, Optional

from pymmcore_plus import CMMCorePlus

MAG_PATTERN = re.compile(r"(\d{1,3})[xX]")
RESOLUTION_ID_PREFIX = "px_size_"


@dataclass
class CoreState:
    """An object to store CMMCore related state.

    This is stuff for which pymmcore.CMMCore doesn't provide an API.
    It could all conceivably be put on the global CMMCorePlus.instance() singleton,
    but for now we maintain an independent state object.
    """

    objectives_device: Optional[str] = None

    __instance: ClassVar[Optional[CoreState]] = None

    @classmethod
    def instance(cls) -> CoreState:
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance


core_state = CoreState.instance()


def update_pixel_size(
    pix_size: Optional[float] = None, mmc: Optional[CMMCorePlus] = None
):
    """Store a pixel config for the

    Parameters
    ----------
    pix_size : float, optional
        _description_, by default None
    mmc : Optional[CMMCorePlus], optional
        _description_, by default None
    """
    if pix_size == 1.0:
        # TODO: this was previous behavior, but does this make sense?
        # presumably it was here because the default value of the spinbox is 1.0?
        return

    mmc = mmc or CMMCorePlus.instance()
    # if pixel size is already set, and we're not providing a new value, return.
    if current_px_size_cfg := mmc.getCurrentPixelSizeConfig():
        if not pix_size:
            return
        mmc.deletePixelSizeConfig(current_px_size_cfg)

    # create and store a new pixel size config for the current objective.
    objective_device = CoreState.instance().objectives_device
    if not objective_device:
        return
    curr_obj = mmc.getProperty(objective_device, "Label")

    # get magnification info from the current objective label
    if match := MAG_PATTERN.search(curr_obj):
        mag = int(match.groups()[0])

        # set image pixel sixe (x,y) for the newly created pixel size config
        resolutionID = f"{RESOLUTION_ID_PREFIX}{curr_obj}"
        mmc.definePixelSizeConfig(resolutionID, objective_device, "Label", curr_obj)
        mmc.setPixelSizeUm(resolutionID, pix_size / mag)
        mmc.setPixelSizeConfig(resolutionID)
