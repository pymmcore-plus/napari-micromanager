"""Functions and utils for managing the global mmcore singleton."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar, List, Optional

from pymmcore_plus import CMMCorePlus

MAG_PATTERN = re.compile(r"(\d{1,3})[xX]")
RESOLUTION_ID_PREFIX = "px_size_"
_SESSION_CORE: Optional[CMMCorePlus] = None


def get_core_singleton(remote=False) -> CMMCorePlus:
    """Retrieve the MMCore singleton for this session.

    The first call to this function determines whether we're running remote or not.
    perhaps a temporary function for now...
    """
    global _SESSION_CORE
    if _SESSION_CORE is None:
        if remote:
            from pymmcore_plus import RemoteMMCore

            _SESSION_CORE = RemoteMMCore()  # type: ignore  # it has the same interface.
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

    def reset(self):
        self.objective_device = None
        self.objectives_cfg = None


STATE = CoreState.instance()


def load_system_config(config: str = ""):
    """Internal convenience for `loadSystemConfiguration(config)`

    This also unloads all devices first and resets the STATE.
    If config is `None` or empty string, will load the MMConfig_demo.
    Note that it should also always be fine for the end-user to use something like
    `CMMCorePlus.instance().loadSystemConfiguration(...)` (instead of this function)
    and we need to handle that as well.  So this function shouldn't get too complex.
    """
    STATE.reset()
    mmc = get_core_singleton()
    mmc.unloadAllDevices()
    mmc.loadSystemConfiguration(config or "MMConfig_demo.cfg")


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


def get_cfg_groups_with_device_label(label: str, max_results=1) -> List[str]:
    """Return config groups that control a device labeled `label`.

    By default, returns a list of length 1 with the first matching config group.

    Parameters
    ----------
    label : str
        A device label
    max_results : int, optional
        The max number of config groups to return, by default 1

    Returns
    -------
    List[str]
        (up to `max_results`) config groups that contain a device named `label`
    """
    mmc = get_core_singleton()
    results = []
    _r = 0
    groups = mmc.getAvailableConfigGroups()
    # we use sorted here to prefer configuration groups with the same name as `label`.
    # in the micromanager docs, `Objective` is used both as the device label and the
    # configuration group name. So, it's worth checking that first.
    for cfg_group in sorted(groups, key=lambda x: x != label):
        for preset in mmc.getAvailableConfigs(cfg_group):
            for device_label, _, _ in mmc.getConfigData(cfg_group, preset):
                if device_label == label:
                    results.append(cfg_group)
                    _r += 1
                    break
            # only need to check the first preset, since preset share the same devices
            break
        if _r >= max_results:
            break
    print("RETT", results)
    return results
