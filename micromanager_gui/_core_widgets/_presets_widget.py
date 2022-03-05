from typing import Optional

from qtpy.QtWidgets import QComboBox, QWidget
from superqt.utils import signals_blocked

from .._core import get_core_singleton


class PresetsWidget(QComboBox):
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

        with signals_blocked(self):
            self.addItems(self._presets)

        self.currentTextChanged.connect(self._on_combo_changed)
        self._mmc.events.configSet.connect(self._on_cfg_set)
        self.destroyed.connect(self._disconnect)

    def _on_combo_changed(self, text: str) -> None:
        self._mmc.setConfig(self._group, text)

    def _on_cfg_set(self, group: str, preset: str) -> None:
        if group == self._group and self.currentText() != preset:
            with signals_blocked(self):
                self.setCurrentText(preset)

    def value(self) -> str:
        return self.currentText()

    def setValue(self, value: str) -> None:
        if value not in self._mmc.getAvailableConfigs(self._group):
            raise ValueError(
                f"{value!r} must be one of {self._mmc.getAvailableConfigs(self._group)}"
            )
        self.setCurrentText(str(value))

    def _disconnect(self):
        self._mmc.events.configSet.disconnect(self._on_cfg_set)
