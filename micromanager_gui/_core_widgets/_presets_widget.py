import warnings
from typing import Optional, Tuple

from pymmcore_plus import DeviceType
from qtpy.QtWidgets import QComboBox, QHBoxLayout, QWidget
from superqt.utils import signals_blocked

from .._core import get_core_singleton
from .._util import get_group_dev_prop, get_preset_dev_prop


class PresetsWidget(QWidget):
    """Create a QCombobox Widget containing the presets of the specified group"""

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

        self.dev_prop = get_group_dev_prop(self._group, self._presets[0])

        self._check_if_presets_have_same_props()

        self._combo = QComboBox()
        self._combo.currentTextChanged.connect(self._update_tooltip)
        self._combo.addItems(self._presets)
        self._combo.setCurrentText(self._mmc.getCurrentConfig(self._group))
        self._set_if_props_match_preset()

        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self._combo)
        self._combo.currentTextChanged.connect(self._on_combo_changed)
        self._combo.textActivated.connect(self._on_text_activate)

        self._mmc.events.configSet.connect(self._on_cfg_set)
        self._mmc.events.systemConfigurationLoaded.connect(self.refresh)
        self._mmc.events.propertyChanged.connect(self._on_property_changed)
        # TODO: add connections once we will implement
        # 'deleteGroup'/'deletePreset signals

        self.destroyed.connect(self.disconnect)

    def _check_if_presets_have_same_props(self):
        n_prop = 0
        for idx, preset in enumerate(self._presets):
            if idx == 0:
                n_prop = len(get_preset_dev_prop(self._group, preset))
                continue

            device_property = get_preset_dev_prop(self._group, preset)

            if len(device_property) != n_prop:
                warnings.warn(f"{self._presets} don't have the same properties")

    def _on_text_activate(self, text: str):
        # used if there is only 1 preset and you want to set it
        self._mmc.setConfig(self._group, text)
        self._combo.setStyleSheet("")

    def _on_combo_changed(self, text: str) -> None:
        self._mmc.setConfig(self._group, text)
        self._combo.setStyleSheet("")

    def _set_if_props_match_preset(self):
        """
        Check if a preset matches the current system state.
        If true, set the combobox to the preset and the text to default color.
        If false, set the combobox text color to 'magenta'.
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
                    self._combo.setStyleSheet("")
                    return
        # if None of the presets match the current system state
        self._combo.setStyleSheet("color: magenta;")

    def _on_cfg_set(self, group: str, preset: str) -> None:
        if group == self._group and self._combo.currentText() != preset:
            with signals_blocked(self._combo):
                self._combo.setCurrentText(preset)
                self._combo.setStyleSheet("")
        else:
            dev_prop_list = get_group_dev_prop(group, preset)
            if any(dev_prop for dev_prop in dev_prop_list if dev_prop in self.dev_prop):
                self._set_if_props_match_preset()

    def _on_property_changed(self, device: str, property: str, value: str):
        if (device, property) not in self.dev_prop:
            if self._mmc.getDeviceType(device) != DeviceType.StateDevice:
                return
            # a StateDevice has also a "Label" property. If "Label" is not
            # in dev_prop, we check if the property "State" is in dev_prop.
            if (device, "State") not in self.dev_prop:
                return
        self._set_if_props_match_preset()

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
                self._combo.setCurrentText(self._mmc.getCurrentConfig(self._group))
                self._set_if_props_match_preset()

    def value(self) -> str:
        return self._combo.currentText()

    def setValue(self, value: str) -> None:
        if value not in self._mmc.getAvailableConfigs(self._group):
            raise ValueError(
                f"{value!r} must be one of {self._mmc.getAvailableConfigs(self._group)}"
            )
        self._combo.setCurrentText(value)

    def allowedValues(self) -> Tuple[str]:
        return tuple(self._combo.itemText(i) for i in range(self._combo.count()))

    def _update_tooltip(self, preset):
        self._combo.setToolTip(
            str(self._mmc.getConfigData(self._group, preset)) if preset else ""
        )

    def disconnect(self):
        self._mmc.events.configSet.disconnect(self._on_cfg_set)
        self._mmc.events.systemConfigurationLoaded.disconnect(self.refresh)
        self._mmc.events.propertyChanged.disconnect(self._on_property_changed)
