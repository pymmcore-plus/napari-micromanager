from typing import Optional, Tuple

from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QComboBox, QHBoxLayout, QWidget
from superqt.utils import signals_blocked

from .._core import get_core_singleton


class PresetsWidget(QWidget):
    """Create a QCombobox Widget for a specified group presets"""

    def __init__(
        self,
        group: str,
        mmcore: Optional[CMMCorePlus] = None,
        parent: Optional[QWidget] = None,
    ) -> None:

        super().__init__(parent)

        self._mmc = mmcore or get_core_singleton()

        self._group = group

        if self._group not in self._mmc.getAvailableConfigGroups():
            raise ValueError(f"{self._group} group does not exist.")

        self._presets = list(self._mmc.getAvailableConfigs(self._group))

        if not self._presets:
            raise ValueError(f"{self._group} group does not have presets.")

        self._combo = QComboBox()
        self._combo.addItems(self._presets)

        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self._combo)
        self._combo.currentTextChanged.connect(self._on_combo_changed)
        self._combo.textActivated.connect(self._on_text_activate)

        self._mmc.events.configSet.connect(self._on_cfg_set)
        self._mmc.events.systemConfigurationLoaded.connect(self.refresh)

        self.destroyed.connect(self.disconnect)

    def _on_text_activate(self, text: str):
        """Used in case there is only one preset"""
        if len(self._presets) == 1:
            self._mmc.setConfig(self._group, text)

    def _on_combo_changed(self, text: str) -> None:
        self._mmc.setConfig(self._group, text)

    def _on_cfg_set(self, group: str, preset: str) -> None:
        if group == self._group and self._combo.currentText() != preset:
            with signals_blocked(self._combo):
                self._combo.setCurrentText(preset)

    def value(self) -> str:
        return self._combo.currentText()

    def setValue(self, value: str) -> None:
        if value not in self._mmc.getAvailableConfigs(self._group):
            raise ValueError(
                f"{value!r} must be one of {self._mmc.getAvailableConfigs(self._group)}"
            )
        self._combo.setCurrentText(str(value))

    def allowedValues(self) -> Tuple[str]:
        return tuple(self._combo.itemText(i) for i in range(self._combo.count()))

    def refresh(self) -> None:
        with signals_blocked(self._combo):
            self._combo.clear()
            if self._group not in self._mmc.getAvailableConfigGroups():
                self._combo.addItem(f"No group named {self._group}.")
                self._combo.setEnabled(False)
            else:
                presets = self._mmc.getAvailableConfigs(self._group)
                self._combo.addItems(presets)
                self._combo.setEnabled(True)

    def disconnect(self):
        self._mmc.events.configSet.disconnect(self._on_cfg_set)
        self._mmc.events.systemConfigurationLoaded.disconnect(self.refresh)
