from typing import Optional

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGroupBox, QHBoxLayout, QWidget

from .. import _core
from .._core_widgets._stage_widget import StageWidget


class MMStagesWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(10, 10, 10, 10)
        self.layout().setSpacing(6)
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
        if dev := self._mmc.getXYStageDevice():
            bx = QGroupBox("XY Control")
            bx.setLayout(QHBoxLayout())
            bx.layout().addWidget(StageWidget(device=dev))
            self.layout().addWidget(bx)
        if dev := self._mmc.getFocusDevice():
            bx = QGroupBox("Z Control")
            bx.setLayout(QHBoxLayout())
            bx.layout().addWidget(StageWidget(device=dev))
            self.layout().addWidget(bx)
        if dev := self._mmc.getAutoFocusDevice():
            bx = QGroupBox("Autofocus Offset")
            bx.setLayout(QHBoxLayout())
            bx.layout().addWidget(StageWidget(device=dev))
            self.layout().addWidget(bx)
        self.resize(self.sizeHint())

    def _clear(self):
        for i in reversed(range(self.layout().count())):
            if item := self.layout().takeAt(i):
                if wdg := item.widget():
                    wdg.setParent(None)
                    wdg.deleteLater()
