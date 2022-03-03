from typing import Any, Optional

from pymmcore_plus import PropertyType
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QWidget
from superqt import QLabeledDoubleSlider, QLabeledSlider

from .._core import get_core_singleton


class PropertyWidget(QWidget):
    def __init__(
        self,
        device_label: str,
        prop_name: str,
        parent: Optional[QWidget] = None,
        orientation=Qt.Orientation.Horizontal,
    ) -> None:
        super().__init__(parent)
        self._mmc = get_core_singleton()

        if device_label not in self._mmc.getLoadedDevices():
            raise ValueError(f"Device not loaded: {device_label!r}")

        if not self._mmc.hasProperty(device_label, prop_name):
            names = self._mmc.getDevicePropertyNames(device_label)
            raise ValueError(
                f"Device {device_label!r} has no property {prop_name!r}. "
                f"Availble property names include: {names}"
            )

        self._device_label = device_label
        self._prop_name = prop_name

        self._prop_type = self._mmc.getPropertyType(device_label, prop_name)
        if self._prop_type is PropertyType.Float:
            self._value_widget = QLabeledDoubleSlider(orientation)
        elif self._prop_type is PropertyType.Integer:
            self._value_widget = QLabeledSlider(orientation)
        elif allowed := self._mmc.getAllowedPropertyValues(device_label, prop_name):
            self._value_widget = QComboBox()
            self._value_widget.addItems(allowed)
        else:
            self._value_widget = QLineEdit()

        if self._mmc.isPropertyReadOnly(device_label, prop_name):
            self._value_widget.setEnabled(False)
        if self._mmc.hasPropertyLimits(device_label, prop_name):
            low = self._mmc.getPropertyLowerLimit(device_label, prop_name)
            up = self._mmc.getPropertyUpperLimit(device_label, prop_name)
            self._value_widget.setMinimum(low)
            self._value_widget.setMaximum(up)

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self._value_widget)

    def value(self) -> Any:
        return self._mmc.getProperty(self._device_label, self._prop_name)
