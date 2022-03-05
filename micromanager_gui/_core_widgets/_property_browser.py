from functools import partial
from typing import Dict, Iterator, Optional, Set, Tuple, cast

from pymmcore_plus import CMMCorePlus, DeviceType
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .._core import get_core_singleton
from ._property_widget import PropertyWidget


def iter_dev_props(mmc: CMMCorePlus) -> Iterator[Tuple[str, str]]:
    for dev in mmc.getLoadedDevices():
        for prop in mmc.getDevicePropertyNames(dev):
            yield dev, prop


class PropertyTable(QTableWidget):
    def __init__(
        self, mmcore: Optional[CMMCorePlus] = None, parent: Optional[QWidget] = None
    ):
        super().__init__(0, 2, parent=parent)
        self._mmc = mmcore or get_core_singleton()

        self.setMinimumWidth(500)
        self.setHorizontalHeaderLabels(["Property", "Value"])
        hdr = self.horizontalHeader()
        hdr.setSectionResizeMode(hdr.ResizeMode.ResizeToContents)
        hdr.setStretchLastSection(True)
        vh = self.verticalHeader()
        vh.setSectionResizeMode(vh.ResizeMode.Fixed)
        vh.setDefaultSectionSize(24)
        vh.setVisible(False)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionMode(self.SelectionMode.NoSelection)
        self.resize(500, 500)
        self._build_table()

    def _build_table(self):
        self.clearContents()
        props = list(iter_dev_props(self._mmc))
        self.setRowCount(len(props))
        for i, (dev, prop) in enumerate(props):
            item = QTableWidgetItem(f"{dev}-{prop}")
            wdg = PropertyWidget(dev, prop, core=self._mmc)
            self.setItem(i, 0, item)
            self.setCellWidget(i, 1, wdg)
            if wdg.isReadOnly():
                item.setBackground(QColor("#CCC"))
                wdg.setStyleSheet("QLabel { background-color : #CCC }")

        # TODO: install eventFilter to prevent mouse wheel from scrolling sliders


DevTypeLabels: Dict[str, DeviceType] = {
    "cameras": DeviceType.CameraDevice,
    "shutters": DeviceType.ShutterDevice,
    "stages": DeviceType.StageDevice,
    "wheels, turrets, etc.": DeviceType.StateDevice,
}
DevTypeLabels["other devices"] = tuple(set(DeviceType) - set(DevTypeLabels.values()))


class PropBrowser(QWidget):
    def __init__(
        self, mmcore: Optional[CMMCorePlus] = None, parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self._mmc = mmcore or get_core_singleton()
        self._prop_table = PropertyTable(mmcore)
        self._show_read_only: bool = True

        self._filters: Set[DeviceType] = set()
        self._filter_text = QLineEdit()
        self._filter_text.setPlaceholderText("Filter...")
        self._filter_text.textChanged.connect(self._update_filter)

        right = QWidget()
        right.setLayout(QVBoxLayout())
        right.layout().addWidget(self._filter_text)
        right.layout().addWidget(self._prop_table)

        left = QWidget()
        left.setLayout(QVBoxLayout())
        left.layout().addWidget(self._make_checkboxes())

        self.setLayout(QHBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(left)
        self.layout().addWidget(right)

    def _update_filter(self):
        filt = self._filter_text.text().lower()
        for r in range(self._prop_table.rowCount()):
            wdg = cast(PropertyWidget, self._prop_table.cellWidget(r, 1))
            if wdg.isReadOnly() and not self._show_read_only:  # sourcery skip
                self._prop_table.hideRow(r)
            elif wdg.deviceType() in self._filters:
                self._prop_table.hideRow(r)
            elif filt and filt not in self._prop_table.item(r, 0).text().lower():
                self._prop_table.hideRow(r)
            else:
                print(wdg.deviceType())
                self._prop_table.showRow(r)

    def _toggle_filter(self, label: str):
        self._filters.symmetric_difference_update({DevTypeLabels[label]})
        self._update_filter()

    def _make_checkboxes(self):
        c = QWidget()
        c.setLayout(QVBoxLayout())
        c.layout().setSpacing(0)

        for label in DevTypeLabels:
            cb = QCheckBox(label)
            cb.setChecked(DevTypeLabels[label] not in self._filters)
            cb.toggled.connect(partial(self._toggle_filter, label))
            c.layout().addWidget(cb)

        ro = QCheckBox("Show read-only")
        ro.setChecked(self._show_read_only)
        ro.toggled.connect(self._set_show_read_only)
        c.layout().addWidget(ro)
        c.layout().addStretch()
        return c

    def _set_show_read_only(self, state: bool):
        self._show_read_only = bool(state)
        self._update_filter()


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication

    CMMCorePlus.instance().loadSystemConfiguration()
    app = QApplication([])

    table = PropBrowser()
    table.show()

    app.exec()
