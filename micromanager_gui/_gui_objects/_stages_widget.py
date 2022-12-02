from typing import Optional

from pymmcore_plus import CMMCorePlus, DeviceType
from pymmcore_widgets import StageWidget
from qtpy.QtCore import QMimeData, Qt
from qtpy.QtGui import QDrag
from qtpy.QtWidgets import QDialog, QGroupBox, QHBoxLayout, QSizePolicy, QWidget

STAGE_DEVICES = {DeviceType.Stage, DeviceType.XYStage}


class MMStagesWidget(QDialog):
    """UI elements for stage control widgets."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setAcceptDrops(True)
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)
        self.setLayout(self.main_layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._mmc = CMMCorePlus.instance()
        self._on_cfg_loaded()
        self._mmc.events.systemConfigurationLoaded.connect(self._on_cfg_loaded)

    def _on_cfg_loaded(self) -> None:
        self._clear()
        sizepolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        stage_dev_list = list(self._mmc.getLoadedDevicesOfType(DeviceType.XYStage))
        stage_dev_list.extend(iter(self._mmc.getLoadedDevicesOfType(DeviceType.Stage)))
        for stage_dev in stage_dev_list:
            if self._mmc.getDeviceType(stage_dev) is DeviceType.XYStage:
                bx = _DragGroupBox("XY Control")
                bx.setLayout(QHBoxLayout())
                bx.setSizePolicy(sizepolicy)
                bx.layout().addWidget(StageWidget(device=stage_dev))
                self.layout().addWidget(bx)
            if self._mmc.getDeviceType(stage_dev) is DeviceType.Stage:
                bx = _DragGroupBox("Z Control")
                bx.setLayout(QHBoxLayout())
                bx.setSizePolicy(sizepolicy)
                bx.layout().addWidget(StageWidget(device=stage_dev))
                self.layout().addWidget(bx)
        self.resize(self.sizeHint())

    def _clear(self) -> None:
        for i in reversed(range(self.layout().count())):
            if item := self.layout().takeAt(i):
                if wdg := item.widget():
                    wdg.setParent(None)
                    wdg.deleteLater()

    def dragEnterEvent(self, event) -> None:
        event.accept()

    def dropEvent(self, event) -> None:
        pos = event.pos()

        wdgs = [
            (
                n,
                self.main_layout.itemAt(n).widget(),
                self.main_layout.itemAt(n).widget().x(),
                self.main_layout.itemAt(n).widget().x()
                + self.main_layout.itemAt(n).widget().size().width(),
            )
            for n in range(self.main_layout.count())
        ]

        zones = [(item[2], item[3]) for item in wdgs]

        for idx, w, _, _ in wdgs:

            if not w.start_pos:
                continue

            try:
                curr_idx = next(
                    (
                        i
                        for i, z in enumerate(zones)
                        if pos.x() >= z[0] and pos.x() <= z[1]
                    )
                )
            except StopIteration:
                break

            if curr_idx == idx:
                w.start_pos = None
                break
            self.main_layout.insertWidget(curr_idx, w)
            w.start_pos = None
            break
        event.accept()


class _DragGroupBox(QGroupBox):
    def __init__(self, name: str, start_pos=None) -> None:
        super().__init__()
        self._name = name
        self.start_pos = start_pos

    def mouseMoveEvent(self, event) -> None:
        drag = QDrag(self)
        mime = QMimeData()
        drag.setMimeData(mime)
        self.start_pos = event.pos().x()
        drag.exec_(Qt.DropAction.MoveAction)