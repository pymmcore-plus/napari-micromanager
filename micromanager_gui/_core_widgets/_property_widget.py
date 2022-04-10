from typing import Any, Callable, Optional, Protocol, Tuple, TypeVar, Union

import pymmcore
from pymmcore_plus import CMMCorePlus, DeviceType, PropertyType
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QWidget,
)
from superqt import QLabeledDoubleSlider, QLabeledSlider, utils

from .._core import get_core_singleton

STATE = pymmcore.g_Keyword_State
LABEL = pymmcore.g_Keyword_Label


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


# -----------------------------------------------------------------------
# These widgets all implement PPropValueWidget for various PropertyTypes.
# -----------------------------------------------------------------------

T = TypeVar("T", bound=float)


def _stretch_range_to_contain(wdg: QLabeledDoubleSlider, val: T) -> T:
    """Set range of `wdg` to include `val`."""
    if val > wdg.maximum():
        wdg.setMaximum(val)
    if val < wdg.minimum():
        wdg.setMinimum(val)
    return val


class IntegerWidget(QSpinBox):
    """Slider suited to managing integer values"""

    def setValue(self, v: Any) -> None:
        return super().setValue(_stretch_range_to_contain(self, int(v)))


class FloatWidget(QDoubleSpinBox):
    """Slider suited to managing float values"""

    def setValue(self, v: Any) -> None:
        # stretch decimals to fit value
        dec = min(str(v).rstrip("0")[::-1].find("."), 8)
        if dec > self.decimals():
            self.setDecimals(dec)
        return super().setValue(_stretch_range_to_contain(self, float(v)))


class _RangedMixin:
    _cast = float

    # prefer horizontal orientation
    def __init__(
        self, orientation=Qt.Orientation.Horizontal, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(orientation, parent)

    def setValue(self: QLabeledSlider, v: float) -> None:
        return super().setValue(_stretch_range_to_contain(self, self._cast(v)))


class RangedIntegerWidget(_RangedMixin, QLabeledSlider):
    """Slider suited to managing ranged integer values"""

    _cast = int


class RangedFloatWidget(_RangedMixin, QLabeledDoubleSlider):
    """Slider suited to managing ranged float values"""


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

    def setValue(self, val: Union[str, int]) -> None:
        return self.setChecked(bool(int(val)))


class ChoiceWidget(QComboBox):
    """Combobox for props with a set of allowed values."""

    valueChanged = Signal(str)

    def __init__(
        self, core: CMMCorePlus, dev: str, prop: str, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._mmc = core
        self._dev = dev
        self._prop = prop
        self._allowed: Tuple[str, ...] = ()

        self._mmc.events.systemConfigurationLoaded.connect(self._refresh_choices)
        self.currentTextChanged.connect(self.valueChanged.emit)
        self.destroyed.connect(self._disconnect)
        self._refresh_choices()

    def _disconnect(self):
        self._mmc.events.systemConfigurationLoaded.disconnect(self._refresh_choices)

    def _refresh_choices(self):
        with utils.signals_blocked(self):
            self.clear()
            self._allowed = self._get_allowed()
            self.addItems(self._allowed)

    def _get_allowed(self) -> Tuple[str, ...]:
        if allowed := self._mmc.getAllowedPropertyValues(self._dev, self._prop):
            return allowed
        if self._mmc.getDeviceType(self._dev) == DeviceType.StateDevice:
            if self._prop == LABEL:
                return self._mmc.getStateLabels(self._dev)
            if self._prop == STATE:
                n_states = self._mmc.getNumberOfStates(self._dev)
                return tuple(str(i) for i in range(n_states))

    def value(self) -> str:
        return self.currentText()

    def setValue(self, value: str) -> None:
        value = str(value)
        # while nice in theory, this check raises unnecessarily when a propertyChanged
        # signal gets emitted during system config loading...
        # if value not in self._allowed:
        #     raise ValueError(f"{value!r} must be one of {self._allowed}")
        self.setCurrentText(value)


class StringWidget(QLineEdit):
    """String widget for pretty much everything else."""

    valueChanged = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.editingFinished.connect(self._emit_value)

    def value(self) -> str:
        return self.text()

    def _emit_value(self):
        self.valueChanged.emit(self.value())

    def setValue(self, value: str) -> None:
        self.setText(str(value))
        self._emit_value()


class ReadOnlyWidget(QLabel):
    """String widget for pretty much everything else."""

    valueChanged = Signal()  # just for the protocol... not used

    def value(self) -> str:
        return self.text()

    def setValue(self, value: str) -> None:
        self.setText(str(value))


# -----------------------------------------------------------------------
# Factory function to create the appropriate PPropValueWidget.
# -----------------------------------------------------------------------


def make_property_value_widget(
    dev: str, prop: str, core: Optional[CMMCorePlus] = None
) -> PPropValueWidget:
    """Return a widget for device `dev`, property `prop`.

    The resulting widget will be used for PropertyWidget._value_widget.

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

    # Create the widget based on property type and allowed choices
    wdg = _creat_prop_widget(core, dev, prop)

    # set current value from core
    wdg.setValue(core.getProperty(dev, prop))

    # connect events and queue for disconnection on widget destroyed
    def _on_core_change(dev_label, prop_name, new_val):
        if dev_label == dev and prop_name == prop:
            with utils.signals_blocked(wdg):
                wdg.setValue(new_val)

    core.events.propertyChanged.connect(_on_core_change)

    @wdg.destroyed.connect
    def _disconnect(*, _core=core):
        try:
            _core.events.propertyChanged.disconnect(_on_core_change)
        except RuntimeError:
            pass

    @wdg.valueChanged.connect
    def _on_widget_change(value, _core=core) -> None:
        # if there's an error when updating core, reset widget value to core
        try:
            _core.setProperty(dev, prop, value)
        except (RuntimeError, ValueError):
            wdg.setValue(_core.getProperty(dev, prop))

    return wdg


def _creat_prop_widget(core: CMMCorePlus, dev: str, prop: str) -> PPropValueWidget:
    """The type -> widget selection part used in the above function."""

    if core.isPropertyReadOnly(dev, prop):
        return ReadOnlyWidget()

    ptype = core.getPropertyType(dev, prop)
    if allowed := core.getAllowedPropertyValues(dev, prop):
        if ptype is PropertyType.Integer and set(allowed) == {"0", "1"}:
            return IntBoolWidget()
        return ChoiceWidget(core, dev, prop)
    if prop in {STATE, LABEL} and core.getDeviceType(dev) == DeviceType.StateDevice:
        # TODO: This logic is very similar to StateDeviceWidget. use this in the future?
        return ChoiceWidget(core, dev, prop)
    if ptype in (PropertyType.Integer, PropertyType.Float):
        if not core.hasPropertyLimits(dev, prop):
            return IntegerWidget() if ptype is PropertyType.Integer else FloatWidget()
        wdg = (
            RangedIntegerWidget()
            if ptype is PropertyType.Integer
            else RangedFloatWidget()
        )
        wdg.setMinimum(wdg._cast(core.getPropertyLowerLimit(dev, prop)))
        wdg.setMaximum(wdg._cast(core.getPropertyUpperLimit(dev, prop)))
        return wdg
    return StringWidget()


# -----------------------------------------------------------------------
# Main public facing QWidget.
# -----------------------------------------------------------------------


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

        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self._value_widget = make_property_value_widget(*self._dp, self._mmc)
        self.layout().addWidget(self._value_widget)

    def value(self) -> Any:
        """Return the current value of the *widget* (which should match core)."""
        return self._value_widget.value()

    def setValue(self, value: Any) -> None:
        """Set the current value of the *widget* (which should match core)."""
        self._value_widget.setValue(value)

    def allowedValues(self) -> Tuple[str, ...]:
        """Return tuple of allowable values if property is categorical."""
        # this will have already been grabbed from core on creation, and will
        # have also taken into account the restrictions in the State/Label property
        # of state devices.  So check for the _allowed attribute on the widget.
        return tuple(getattr(self._value_widget, "_allowed", ()))

    def refresh(self) -> None:
        """Update the value of the widget from core.

        (If all goes well this shouldn't be necessary, but if a propertyChanged
        event is missed, this can be used).
        """
        with utils.signals_blocked(self._value_widget):
            self._value_widget.setValue(self._mmc.getProperty(*self._dp))

    def propertyType(self) -> PropertyType:
        """Return property type."""
        return self._mmc.getPropertyType(*self._dp)

    def deviceType(self) -> DeviceType:
        """Return property type."""
        return self._mmc.getDeviceType(self._device_label)

    def isReadOnly(self) -> bool:
        """Return True if property is read only."""
        return self._mmc.isPropertyReadOnly(*self._dp)

    @property
    def _dp(self) -> Tuple[str, str]:
        """commonly requested pair for mmcore calls."""
        return self._device_label, self._prop_name
