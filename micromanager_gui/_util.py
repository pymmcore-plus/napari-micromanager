from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from qtpy.QtWidgets import QWidget

if TYPE_CHECKING:
    import useq
    from pymmcore_plus import RemoteMMCore


def get_devices_and_props(self):
    mmc = None
    # List devices and properties that you can set
    devices = mmc.getLoadedDevices()
    print("\nDevice status:__________________________")
    for i in range(len(devices)):
        device = devices[i]
        properties = mmc.getDevicePropertyNames(device)
        for p in range(len(properties)):
            prop = properties[p]
            values = mmc.getAllowedPropertyValues(device, prop)
            print(f"Device: {str(device)}  Property: {str(prop)} Value: {str(values)}")
    print("________________________________________")


def get_groups_list(self):
    mmc = None
    group = []
    for groupName in mmc.getAvailableConfigGroups():
        print(f"*********\nGroup_Name: {str(groupName)}")
        for configName in mmc.getAvailableConfigs(groupName):
            group.append(configName)
            print(f"Config_Name: {str(configName)}")
            props = str(mmc.getConfigData(groupName, configName).getVerbose())
            print(f"Properties: {props}")
        print("*********")


def extend_array_for_index(array: np.ndarray, index: tuple[int, ...]):
    """Return `array` padded with zeros if necessary to contain `index`."""

    # if the incoming index is outside of the bounds of the current layer.data
    # pad layer.data with zeros to accomodate the incoming index
    if any(x >= y for x, y in zip(index, array.shape)):
        newshape = list(array.shape)
        for i, (x, y) in enumerate(zip(index, array.shape)):
            newshape[i] = max(x + 1, y)

        new_array = np.zeros(newshape)
        # populate with existing data
        new_array[tuple(slice(s) for s in array.shape)] = array
        return new_array

    # otherwise just return the incoming array
    return array


def ensure_unique(path: Path, extension: str = ".tif", ndigits: int = 3):
    """
    Get next suitable filepath (extension = ".tif") or
    folderpath (extension = ""), appended with a counter of ndigits.
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
def event_indices(event: useq.MDAEvent):
    for k in event.sequence.axis_order if event.sequence else []:
        if k in event.index:
            yield k


@contextmanager
def blockSignals(widgets: QWidget | list[QWidget]):
    if not isinstance(widgets, (list, tuple)):
        widgets = [widgets]
    orig_states = []
    for w in widgets:
        orig_states.append(w.signalsBlocked())
        w.blockSignals(True)
    yield
    for w, s in zip(widgets, orig_states):
        w.blockSignals(s)


class AutofocusDevice:
    def __init__(self, mmcore: RemoteMMCore):
        super().__init__()
        self._mmc = mmcore

    @classmethod
    def create(self, key):
        if key == "TIPFS":
            return NikonPFS()


class NikonPFS(AutofocusDevice):
    # for Nikon PFS:
    # mmcore.getAutoFocusDevice() -> "TIPFStatus"
    # to get/change the offset use -> "TIPFSOffset" "Position" mmcore Property
    def set_offset(self, offset: float) -> None:
        self._mmc.setProperty("TIPFSOffset", "Position", offset)

    def get_position(self) -> str:
        self._mmc.getProperty("TIPFSOffset", "Position")
