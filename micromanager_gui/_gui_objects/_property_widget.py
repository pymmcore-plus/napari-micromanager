from typing import Any, Callable, Optional, Protocol

from psygnal import SignalInstance
from pymmcore_plus import PropertyType
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLineEdit, QWidget
from superqt import QLabeledDoubleSlider, QLabeledSlider

from .._core import get_core_singleton


class PSignalInstance(Protocol):
    def connect(self, callback: Callable) -> Callable:
        ...

    def disconnect(self, callback: Callable) -> None:
        ...

    def emit(self, *args: Any) -> None:
        ...


class PPropValueWidget(Protocol):
    def value(self) -> Any:
        ...

    def setValue(self) -> Any:
        ...

    def setEnabled(self, enabled: bool) -> None:
        ...

    @property
    def valueChanged(self) -> PSignalInstance:
        ...

    @property
    def destroyed(self) -> SignalInstance:
        ...

    def setParent(self, parent: Optional[QWidget]) -> None:
        ...

    def deleteLater(self) -> None:
        ...


class IntegerWidget(QLabeledSlider):
    def __init__(
        self, orientation=Qt.Horizontal, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(orientation, parent)


class FloatWidget(QLabeledDoubleSlider):
    def __init__(
        self, orientation=Qt.Horizontal, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(orientation, parent)


class IntBoolWidget(QCheckBox):
    valueChanged = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.toggled.connect(self._emit)

    def _emit(self, state: bool):
        self.valueChanged.emit(int(state))

    def value(self) -> int:
        return int(self.isChecked())

    def setValue(self, val: int) -> None:
        return self.setChecked(bool(val))


class ChoiceWidget(QComboBox):
    valueChanged = Signal(str)

    def __init__(self, allowed=(), parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.currentTextChanged.connect(self.valueChanged.emit)
        self._allowed = allowed
        if allowed:
            self.addItems(allowed)

    def value(self) -> str:
        return self.currentText()

    def setValue(self, value: str) -> None:
        if value not in self._allowed:
            raise ValueError(f"{value!r} must be one of {self._allowed}")
        self.setCurrentText(str(value))


class StringWidget(QLineEdit):
    valueChanged = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.textChanged.connect(self.valueChanged.emit)

    def value(self) -> str:
        return self.text()

    def setValue(self, value: str) -> None:
        self.setText(str(value))


def _make_prop_widget(dev: str, prop: str) -> PPropValueWidget:
    core = get_core_singleton()
    _type = core.getPropertyType(dev, prop)

    if allowed := core.getAllowedPropertyValues(dev, prop):
        # note: many string properties are also choices between "Yes", "No"
        if _type is PropertyType.Integer and set(allowed) == {"0", "1"}:
            wdg = IntBoolWidget()
        else:
            wdg = ChoiceWidget(allowed)
    elif _type in (PropertyType.Integer, PropertyType.Float):
        wdg = IntegerWidget() if _type is PropertyType.Integer else FloatWidget()
        if core.hasPropertyLimits(dev, prop):
            wdg.setMinimum(core.getPropertyLowerLimit(dev, prop))
            wdg.setMaximum(core.getPropertyUpperLimit(dev, prop))
    else:
        wdg = StringWidget()
    if core.isPropertyReadOnly(dev, prop):
        if hasattr(wdg, "setReadOnly"):
            wdg.setReadOnly(True)
        wdg.setEnabled(False)
    return wdg


class PropertyWidget(QWidget):
    _value_widget: PPropValueWidget
    valueChanged = Signal(object)

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

        self.setLayout(QHBoxLayout())
        self._build_value_widget()

    def _build_value_widget(self) -> None:
        if hasattr(self, "_value_widget"):
            self._value_widget.setParent(None)
            self._value_widget.deleteLater()

        self._value_widget = _make_prop_widget(self._device_label, self._prop_name)
        self._value_widget.valueChanged.connect(self._update_core)
        self._value_widget.destroyed.connect(self._disconnect)
        self.layout().addWidget(self._value_widget)

    def _disconnect(self):
        self._value_widget.destroyed.disconnect(self._disconnect)

    def _update_core(self, value) -> None:
        self._mmc.setProperty(self._device_label, self._prop_name, value)

    def value(self) -> Any:
        return self._value_widget.value()

    def setValue(self, value):
        self._value_widget.setValue(value)
