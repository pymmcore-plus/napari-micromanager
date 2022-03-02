from typing import Any, Optional, Tuple, TypeVar

from pymmcore_plus import DeviceType
from qtpy.QtWidgets import QComboBox, QHBoxLayout, QWidget
from superqt.utils import signals_blocked

from .._core import get_core_singleton

T = TypeVar("T", bound="DeviceWidget")


class DeviceWidget(QWidget):
    """Base Device Widget.

    Use `DeviceWidget.for_device('someLabel')` to create the device-type
    appropriate subclass.
    """

    def __init__(self, device_label: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._device_label = device_label
        self._mmc = get_core_singleton()

    def deviceName(self) -> str:
        return self._mmc.getDeviceName(self._device_label)

    def deviceLabel(self) -> str:
        return self._device_label

    @classmethod
    def for_device(cls, label: str):
        core = get_core_singleton()
        dev_type = core.getDeviceType(label)
        _map = {DeviceType.StateDevice: StateDeviceWidget}
        return _map[dev_type](label)


class StateDeviceWidget(DeviceWidget):
    """Widget to control a StateDevice."""

    def __init__(self, device_label: str, parent: Optional[QWidget] = None):
        super().__init__(device_label, parent)
        assert self._mmc.getDeviceType(device_label) == DeviceType.StateDevice

        self._combo = QComboBox()
        self._combo.currentIndexChanged.connect(self._on_combo_changed)
        self._refresh_combo_choices()
        self._combo.setCurrentText(self._mmc.getStateLabel(self._device_label))

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self._combo)

        self._mmc.events.propertyChanged.connect(self._on_prop_change)
        self.destroyed.connect(self._disconnect)

    def _on_combo_changed(self, index: int) -> None:
        # TODO: add hook here for pre change/post change?
        # e.g. if you wanted to drop the objective before changing
        self._mmc.setState(self._device_label, index)

    def _disconnect(self):
        self._mmc.events.propertyChanged.disconnect(self._on_prop_change)

    def _on_prop_change(self, dev_label: str, prop: str, value: Any):
        # TODO: hmmm... it appears that not all state devices emit
        # a property change event?
        print("PROP CHANGE", locals())
        if dev_label == self._device_label:
            with signals_blocked(self._combo):
                self._combo.setCurrentText(value)

    def _refresh_combo_choices(self):
        with signals_blocked(self._combo):
            self._combo.clear()
            self._combo.addItems(self.stateLabels())

    def state(self) -> int:
        return self._mmc.getState(self._device_label)

    def data(self):
        return self._mmc.getData(self._device_label)

    def stateLabel(self) -> str:
        return self._mmc.getStateLabel(self._device_label)

    def stateLabels(self) -> Tuple[str]:
        return self._mmc.getStateLabels(self._device_label)
