from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton, QWidget

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


class SelectDeviceFromCombobox(QDialog):
    val_changed = Signal(str)

    def __init__(self, obj_dev: list, label: str, parent=None):
        super().__init__(parent)

        self.setLayout(QHBoxLayout())
        self.label = QLabel()
        self.label.setText(label)
        self.combobox = QComboBox()
        self.combobox.addItems(obj_dev)
        self.button = QPushButton("Set")
        self.button.clicked.connect(self._on_click)

        self.layout().addWidget(self.label)
        self.layout().addWidget(self.combobox)
        self.layout().addWidget(self.button)

    def _on_click(self):
        self.val_changed.emit(self.combobox.currentText())


# This could maybe be a per camera device cache in cases with multiple cameras
# work for the future - let the good be the enemy of the perfect rather than
# the other way around!
class ExposureCache:
    def __init__(
        self, mmc: RemoteMMCore, channel_group: str = None, fallback_value: float = 1
    ) -> None:
        self._mmc = mmc
        self._fallback_value = fallback_value
        self._cache = defaultdict(lambda: fallback_value)
        if channel_group is None:
            # don't guess about channel groups
            # just let that be set elsewhere
            self._channel_group: str = self._mmc.getChannelGroup()
        else:
            self._channel_group: str = channel_group

    @property
    def channel_group(self):
        return self._channel_group

    @channel_group.setter
    def channel_group(self, value: str):
        if not isinstance(value, str):
            raise TypeError("channel_group must be a string.")
        if value != self._channel_group:
            # invalidate the cache
            self._cache = defaultdict(lambda: self._fallback_value)
            self._channel_group = value

    def update_cache(self, channel: str, exposure: float = None):
        """Update the values in the cache, inferring as needed."""
        # Need to require channel because there is no way to infer that from MM
        # in the future once that's more easily inferrable allow either as optional
        # if channel is None:
        #     channel = self._mmc.getCurrentConfigFromCache(self._channel_group)
        if exposure is None:
            exposure = self._mmc.getExposure()
        self._cache[channel] = exposure

    def __getitem__(self, channel: str) -> float:
        if self._channel_group in self._mmc.getAvailableConfigGroups() and channel:
            cfg = self._mmc.getConfigData(self._channel_group, channel)
            cam_device = self._mmc.getCameraDevice()
            if (cam_device, "Exposure") in cfg:
                exposure = float(cfg[(cam_device, "Exposure")])
                self._cache[channel] = exposure
                return exposure
            else:
                return self._cache[channel]
        else:
            return self._fallback_value

    def __setitem__(self, channel: str, exposure: float):
        self._cache[channel] = exposure
