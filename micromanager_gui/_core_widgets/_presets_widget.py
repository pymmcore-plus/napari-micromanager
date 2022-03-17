from typing import Optional, Tuple

from pymmcore_plus import DeviceType
from qtpy.QtWidgets import QComboBox, QHBoxLayout, QWidget
from superqt.utils import signals_blocked

from .._core import get_core_singleton
from .._util import get_dev_prop, set_wdg_color


class PresetsWidget(QWidget):
    """Create a QCombobox Widget for a specified group presets"""

    def __init__(
        self,
        group: str,
        text_color: str = "black",
        parent: Optional[QWidget] = None,
    ) -> None:

        super().__init__(parent)

        self._mmc = get_core_singleton()

        self._group = group
        self.text_color = text_color

        if self._group not in self._mmc.getAvailableConfigGroups():
            raise ValueError(f"{self._group} group does not exist.")

        self._presets = list(self._mmc.getAvailableConfigs(self._group))

        if not self._presets:
            raise ValueError(f"{self._group} group does not have presets.")

        self.dev_prop = get_dev_prop(self._group, self._presets[0])

        self._check_if_presets_have_same_props()

        self._combo = QComboBox()
        self._combo.addItems(self._presets)

        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self._combo)
        set_wdg_color(self.text_color, self._combo)
        self._combo.currentTextChanged.connect(self._on_combo_changed)
        self._combo.textActivated.connect(self._on_text_activate)

        self._mmc.events.configSet.connect(self._on_cfg_set)
        self._mmc.events.systemConfigurationLoaded.connect(self.refresh)
        self._mmc.events.propertyChanged.connect(self._highlight_if_prop_changed)

        self.destroyed.connect(self.disconnect)

    def _check_if_presets_have_same_props(self):
        for idx, preset in enumerate(self._presets):
            if idx == 0:
                continue
            device_property = get_dev_prop(self._group, preset)
            if len(device_property) != len(self.dev_prop):
                raise ValueError(f"{self._presets} must have the same properties.")

    def _on_text_activate(self, text: str):
        """Used in case there is only one preset"""
        if len(self._presets) == 1:
            self._mmc.setConfig(self._group, text)
            set_wdg_color(self.text_color, self._combo)

    def _on_combo_changed(self, text: str) -> None:
        self._mmc.setConfig(self._group, text)
        set_wdg_color(self.text_color, self._combo)

    def _on_cfg_set(self, group: str, preset: str) -> None:
        if group == self._group and self._combo.currentText() != preset:
            with signals_blocked(self._combo):
                self._combo.setCurrentText(preset)
                set_wdg_color(self.text_color, self._combo)
        else:
            dev_prop_list = get_dev_prop(group, preset)
            if any(dev_prop for dev_prop in dev_prop_list if dev_prop in self.dev_prop):
                self._set_if_props_match_preset()

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

    def _highlight_if_prop_changed(self, device: str, property: str, value: str):
        if (device, property) not in self.dev_prop:
            if self._mmc.getDeviceType(device) != DeviceType.StateDevice:
                return
            # a StateDevice has also a "Label" property. If "Label" is not
            # in dev_prop, we check if the property "State" is in dev_prop.
            if (device, "State") not in self.dev_prop:
                return
        self._set_if_props_match_preset()

    def _set_if_props_match_preset(self):
        """
        Check if a preset matches the current system state.
        If true, set the combobox to the preset with 'text_color'.
        If false, set the combobox color to 'magenta'.
        """
        for preset in self._presets:
            _set_combo = True
            for (dev, prop, value) in self._mmc.getConfigData(self._group, preset):
                cache_value = self._mmc.getPropertyFromCache(dev, prop)
                if cache_value != value:
                    _set_combo = False
                    break
            if _set_combo:
                with signals_blocked(self._combo):
                    self._combo.setCurrentText(preset)
                    set_wdg_color(self.text_color, self._combo)
                    return
        # None of the presets match the current system state
        set_wdg_color("magenta", self._combo)

    def disconnect(self):
        self._mmc.events.configSet.disconnect(self._on_cfg_set)
        self._mmc.events.systemConfigurationLoaded.disconnect(self.refresh)
        self._mmc.events.propertyChanged.disconnect(self._highlight_if_prop_changed)
