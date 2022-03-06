from typing import Optional, Tuple

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
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self._combo)

        self._combo.currentTextChanged.connect(self._on_combo_changed)
        self._mmc.events.configSet.connect(self._on_cfg_set)
        self._mmc.events.systemConfigurationLoaded.connect(self.refresh)
        self._mmc.events.propertyChanged.connect(self._highlight_if_prop_changed)
        self.destroyed.connect(self._disconnect)

    def _on_combo_changed(self, text: str) -> None:
        self._mmc.setConfig(self._group, text)
        self._set_font_color("black")

    def _on_cfg_set(self, group: str, preset: str) -> None:
        if group == self._group and self._combo.currentText() != preset:
            with signals_blocked(self._combo):
                self._combo.setCurrentText(preset)
                self._set_font_color("black")

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

    def _set_font_color(self, color: str = "black"):
        self._combo.setEditable(True)
        self._combo.setStyleSheet(f"color: {color};")
        self._combo.setEditable(False)

    def _highlight_if_prop_changed(self, device: str, property: str, value: str):

        dev_prop = [
            (k[0], k[1]) for k in self._mmc.getConfigData(self._group, self._presets[0])
        ]

        if (device, property) not in dev_prop:
            return

        if not self._mmc.getCurrentConfig(self._group):
            self._set_font_color("magenta")
        else:
            self._set_font_color("black")

    def _disconnect(self):
        self._mmc.events.configSet.disconnect(self._on_cfg_set)
