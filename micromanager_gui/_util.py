from pathlib import Path
from typing import Tuple

import numpy as np


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


def extend_array_for_index(array: np.ndarray, index: Tuple[int, ...]):
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
    if extension == "":
        for fn in p.parent.glob("*"):
            if fn.is_dir():
                try:
                    current_max = max(current_max, int(fn.stem.rsplit("_")[-1]))
                except ValueError:
                    continue
    # # find the highest existing path (if e.g. .tif)
    else:
        for fn in p.parent.glob(f"*{extension}"):
            try:
                current_max = max(current_max, int(fn.stem.rsplit("_")[-1]))
            except ValueError:
                continue

    # build new path name
    number = f"_{current_max+1:0{ndigits}d}"

    if extension:
        return path.parent / f"{stem}{number}{extension}"
    else:
        return path.parent / f"{stem}{number}"
