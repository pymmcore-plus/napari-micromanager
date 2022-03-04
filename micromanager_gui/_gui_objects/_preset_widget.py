from typing import Optional

from qtpy.QtWidgets import QComboBox, QHBoxLayout, QWidget
from superqt.utils import signals_blocked

from .._core import get_core_singleton


class PresetsWidget(QWidget):
    """Create a QCombobox Widget for a specified group presets"""

    def __init__(
        self,
        group: str,
        parent: Optional[QWidget] = None,
    ) -> None:

        super().__init__(parent)

        self._mmc = get_core_singleton()

        self._group = group

        if self._group not in self._mmc.getAvailableConfigGroups():
            raise ValueError(f"{self._group} group does not exist.")

        self._presets = list(self._mmc.getAvailableConfigs(self._group))

        if not self._presets:
            raise ValueError(f"{self._group} group does not have presets.")

        self._combo = QComboBox()
        self._combo.addItems(self._presets)
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self._combo)

        self._combo.currentTextChanged.connect(self._on_combo_changed)
        self._mmc.events.configSet.connect(self._on_cfg_set)
        self.destroyed.connect(self._disconnect)

    def _on_combo_changed(self, text: str) -> None:
        self._mmc.setConfig(self._group, text)
        print(f"cfg set: {self._group} -> {text}")

    def _on_cfg_set(self, group: str, preset: str):
        if group == self._group:
            with signals_blocked(self._combo):
                self._combo.setCurrentText(preset)
                print(f"cfg changed to {self._group} -> {preset}")

    def _disconnect(self):
        self._mmc.events.configSet.disconnect(self._on_cfg_set)
