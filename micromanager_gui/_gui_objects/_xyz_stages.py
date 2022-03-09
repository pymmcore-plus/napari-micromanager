from qtpy.QtWidgets import QHBoxLayout, QWidget

from .. import _core
from .._core_widgets._stage_widget import StageWidget


class MMStagesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self._mmc = _core.get_core_singleton()
        self._on_cfg_loaded()
        self._mmc.events.systemConfigurationLoaded.connect(self._on_cfg_loaded)

    def _on_cfg_loaded(self):
        self._clear()
        if dev := self._mmc.getXYStageDevice():
            self.layout().addWidget(StageWidget(device=dev))
        if dev := self._mmc.getFocusDevice():
            self.layout().addWidget(StageWidget(device=dev))
        if dev := self._mmc.getAutoFocusDevice():
            self.layout().addWidget(StageWidget(device=dev))
        self.resize(self.sizeHint())

    def _clear(self):
        for i in range(self.layout().count()):
            if item := self.layout().takeAt(i):
                if wdg := item.widget():
                    wdg.setParent(None)
                    wdg.deleteLater()
