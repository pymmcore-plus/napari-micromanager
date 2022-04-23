from typing import Optional

from pymmcore_plus import DeviceType
from qtpy.QtCore import QMimeData, Qt
from qtpy.QtGui import QDrag
from qtpy.QtWidgets import QGroupBox, QHBoxLayout, QWidget

from .. import _core
from .._core_widgets._stage_widget import StageWidget

STAGE_DEVICES = {DeviceType.Stage, DeviceType.XYStage}


class MMStagesWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(6)
        self.setLayout(self.main_layout)

        self._mmc = _core.get_core_singleton()
        self._on_cfg_loaded()
        self._mmc.events.systemConfigurationLoaded.connect(self._on_cfg_loaded)

        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )

    def _on_cfg_loaded(self):
        self._clear()
        stage_dev_list = [
            dev
            for dev in self._mmc.getLoadedDevices()
            if self._mmc.getDeviceType(dev) in STAGE_DEVICES
        ]
        stage_dev_list.sort()
        for stage_dev in stage_dev_list:
            if self._mmc.getDeviceType(stage_dev) is DeviceType.XYStage:
                bx = DragGroupBox("XY Control")
                bx.setLayout(QHBoxLayout())
                bx.layout().addWidget(StageWidget(device=stage_dev))
                self.layout().addWidget(bx)
            if self._mmc.getDeviceType(stage_dev) is DeviceType.Stage:
                bx = DragGroupBox("Z Control")
                bx.setLayout(QHBoxLayout())
                bx.layout().addWidget(StageWidget(device=stage_dev))
                self.layout().addWidget(bx)
        self.resize(self.sizeHint())

    def _clear(self):
        for i in reversed(range(self.layout().count())):
            if item := self.layout().takeAt(i):
                if wdg := item.widget():
                    wdg.setParent(None)
                    wdg.deleteLater()

    def dragEnterEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        pos = event.pos()
        widget = event.source()

        print(pos)

        for n in range(self.main_layout.count()):
            # Get the widget at each index in turn.
            w = self.main_layout.itemAt(n).widget()
            print(pos.x(), w.x(), w.size().width())
            if pos.x() < w.x():
                self.main_layout.insertWidget(n - 1, widget)
            elif pos.x() > w.x():
                self.main_layout.insertWidget(n, widget)
        event.accept()


class DragGroupBox(QGroupBox):
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            drag.setMimeData(mime)
            drag.exec_(Qt.MoveAction)
