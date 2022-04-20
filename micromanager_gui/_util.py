from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Sequence, Tuple

import numpy as np
from pymmcore_plus import CMMCorePlus
from qtpy.QtCore import Signal
from qtpy.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ._core import get_core_singleton

if TYPE_CHECKING:
    import useq


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


class ComboMessageBox(QDialog):
    """Dialog that presents a combo box of `items`."""

    def __init__(
        self,
        items: Sequence[str] = (),
        text: str = "",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._combo = QComboBox()
        self._combo.addItems(items)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        self.setLayout(QVBoxLayout())
        if text:
            self.layout().addWidget(QLabel(text))
        self.layout().addWidget(self._combo)
        self.layout().addWidget(btn_box)

    def currentText(self) -> str:
        return self._combo.currentText()


def get_preset_dev_prop(
    group: str, preset: str, mmcore: Optional[CMMCorePlus] = None
) -> list:
    """Return a list with (device, property) for the selected group preset"""
    mmc = mmcore or get_core_singleton()
    return [(k[0], k[1]) for k in mmc.getConfigData(group, preset)]


def get_group_dev_prop(
    group: str, preset: str, mmcore: Optional[CMMCorePlus] = None
) -> List[Tuple[str, str]]:
    """
    Return a list of all (device, property) tuples used in the config group's presets
    """
    mmc = mmcore or get_core_singleton()
    dev_props = []
    for preset in mmc.getAvailableConfigs(group):
        dev_props.extend([(k[0], k[1]) for k in mmc.getConfigData(group, preset)])
    return dev_props
