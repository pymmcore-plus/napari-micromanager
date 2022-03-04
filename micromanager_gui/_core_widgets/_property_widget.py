from typing import Any, Callable, Optional, Protocol, TypeVar, Union, cast

from pymmcore_plus import CMMCorePlus, PropertyType
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLineEdit, QWidget
from superqt import QLabeledDoubleSlider, QLabeledSlider, utils

from .._core import get_core_singleton


# fmt: off
class PSignalInstance(Protocol):
    """The protocol expected of a signal instance"""
    def connect(self, callback: Callable) -> Callable: ...
    def disconnect(self, callback: Callable) -> None: ...
    def emit(self, *args: Any) -> None: ...


class PPropValueWidget(Protocol):
    """The protocol expected of a ValueWidget."""
    valueChanged: PSignalInstance
    destroyed: PSignalInstance
    def value(self) -> Union[str, float]: ...
    def setValue(self, val: Union[str, float]) -> None: ...
    def setEnabled(self, enabled: bool) -> None: ...
    def setParent(self, parent: Optional[QWidget]) -> None: ...
    def deleteLater(self) -> None: ...
# fmt: on


T = TypeVar("T", bound=float)


def _stretch_range_to_contain(wdg: QLabeledDoubleSlider, val: T) -> T:
    """Set range of `wdg` to include `val`."""
    if val > wdg.maximum():
        wdg.setMaximum(val)
    if val < wdg.minimum():
        wdg.setMinimum(val)
    return val


class IntegerWidget(QLabeledSlider):
    """Slider suited to managing integer values"""

    def __init__(
        self, orientation=Qt.Horizontal, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(orientation, parent)

    def setValue(self, v: int) -> None:
        return super().setValue(_stretch_range_to_contain(self, int(v)))


class FloatWidget(QLabeledDoubleSlider):
    """Slider suited to managing float values"""

    def __init__(
        self, orientation=Qt.Horizontal, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(orientation, parent)

    def setValue(self, v: float) -> None:
        return super().setValue(_stretch_range_to_contain(self, float(v)))


class IntBoolWidget(QCheckBox):
    """Checkbox for boolean values, which are integers in pymmcore"""

    valueChanged = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.toggled.connect(self._emit)

    def _emit(self, state: bool):
        self.valueChanged.emit(int(state))

    def value(self) -> int:
        return int(self.isChecked())

    def setValue(self, val: int) -> None:
        return self.setChecked(bool(int(val)))


class ChoiceWidget(QComboBox):
    """Combobox for props with a set of allowed values."""

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
    """String widget for pretty much everything else."""

    valueChanged = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.textChanged.connect(self.valueChanged.emit)

    def value(self) -> str:
        return self.text()

    def setValue(self, value: str) -> None:
        self.setText(str(value))


def make_property_widget(
    dev: str, prop: str, core: Optional[CMMCorePlus] = None
) -> PPropValueWidget:
    """Return a widget for device `dev`, property `prop`.

    Parameters
    ----------
    dev : str
        Device label
    prop : str
        Property name
    core : Optional[CMMCorePlus]
        Optional CMMCorePlus instance, by default the global singleton.

    Returns
    -------
    PPropValueWidget
        A widget with a normalized PropValueWidget protocol.
    """
    core = core or get_core_singleton()
    _type = core.getPropertyType(dev, prop)

    # Create the widget based on property type and allowed choices
    if allowed := core.getAllowedPropertyValues(dev, prop):
        # note: many string properties are also choices between "Yes", "No"
        if _type is PropertyType.Integer and set(allowed) == {"0", "1"}:
            wdg = IntBoolWidget()
        else:
            wdg = ChoiceWidget(allowed)
    elif _type in (PropertyType.Integer, PropertyType.Float):
        wdg = IntegerWidget() if _type is PropertyType.Integer else FloatWidget()
        if core.hasPropertyLimits(dev, prop):
            wdg.setMinimum(_type.to_python()(core.getPropertyLowerLimit(dev, prop)))
            wdg.setMaximum(_type.to_python()(core.getPropertyUpperLimit(dev, prop)))
    else:
        wdg = StringWidget()

    # set current value from core
    wdg.setValue(core.getProperty(dev, prop))

    # disable if read only
    if core.isPropertyReadOnly(dev, prop):
        if hasattr(wdg, "setReadOnly"):
            wdg.setReadOnly(True)
        wdg.setEnabled(False)

    # connect events and queue for disconnection on widget destroyed
    def _on_core_change(dev_label, prop_name, new_val):
        if dev_label == dev and prop_name == prop:
            with utils.signals_blocked(wdg):
                wdg.setValue(new_val)

    core.events.propertyChanged.connect(_on_core_change)
    wdg = cast(PPropValueWidget, wdg)
    wdg.destroyed.connect(
        lambda: core.events.propertyChanged.disconnect(_on_core_change)
    )

    @wdg.valueChanged.connect
    def _on_widget_change(value) -> None:
        core.setProperty(dev, prop, value)

    return wdg


class PropertyWidget(QWidget):
    """A widget that presents a view onto an mmcore device property.

    Parameters
    ----------
    device_label : str
        Device label
    prop_name : str
        Property name
    parent : Optional[QWidget]
        parent widget, by default None
    core : Optional[CMMCorePlus]
        Optional CMMCorePlus instance, by default the global singleton.

    Raises
    ------
    ValueError
        If the `device_label` is not loaded, or does not have a property `prop_name`.
    """

    _value_widget: PPropValueWidget
    valueChanged = Signal(object)

    def __init__(
        self,
        device_label: str,
        prop_name: str,
        *,
        parent: Optional[QWidget] = None,
        core: Optional[CMMCorePlus] = None,
    ) -> None:
        super().__init__(parent)
        self._mmc = core or get_core_singleton()
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
        """Create widget for device_label/prop_name, and add to layout."""
        if hasattr(self, "_value_widget"):
            self._value_widget.setParent(None)
            self._value_widget.deleteLater()

        self._value_widget = make_property_widget(
            self._device_label, self._prop_name, self._mmc
        )
        self.layout().addWidget(self._value_widget)

    def value(self) -> Any:
        """Return the current value of the *widget*."""
        return self._value_widget.value()

    def setValue(self, value: Any) -> None:
        """Set the current value of the *widget*."""
        self._value_widget.setValue(value)

    def refresh(self) -> None:
        """Set the value of the widget to core.

        (If all goes well this shouldn't be necessary, but if a propertyChanged
        event is missed, this can be used).
        """
        val = self._mmc.getProperty(self._device_label, self._prop_name)
        with utils.signals_blocked(self._value_widget):
            self._value_widget.setValue(val)
