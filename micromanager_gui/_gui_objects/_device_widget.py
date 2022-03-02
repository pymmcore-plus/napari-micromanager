from typing import Any, Optional, Tuple, TypeVar

from pymmcore_plus import CMMCorePlus, DeviceType
from qtpy.QtWidgets import QComboBox, QHBoxLayout, QWidget

T = TypeVar("T", bound="DeviceWidget")


class DeviceWidget(QWidget):
    """Base Device Widget.

    Use `DeviceWidget.for_device('someLabel')` to create the device-type
    appropriate subclass.
    """

    def __init__(self, device_label: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._device_label = device_label
        self._mmc = CMMCorePlus.instance()

    def deviceName(self) -> str:
        return self._mmc.getDeviceName()

    @classmethod
    def for_device(cls, label: str):
        core = CMMCorePlus.instance()
        dt = core.getDeviceType("Objective")
        _map = {DeviceType.StateDevice: StateDeviceWidget}
        return _map[dt](label)


class StateDeviceWidget(DeviceWidget):
    """Widget to control a StateDevice."""

    def __init__(self, device_label: str, parent: Optional[QWidget] = None):
        super().__init__(device_label, parent)
        assert self._mmc.getDeviceType(device_label) == DeviceType.StateDevice

        self._combo = QComboBox()
        self._combo.currentIndexChanged.connect(self._on_combo_changed)
        self._refresh_combo()

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self._combo)

        self._mmc.events.propertyChanged.connect(self._on_prop_change)
        self.destroyed.connect(self._disconnect)

    def _on_combo_changed(self, index: int) -> None:
        # TODO: add hook here for pre change/post change
        # e.g. if you wanted to drop the objective before changing
        self._mmc.setState(self._device_label, index)

    def _disconnect(self):
        self._mmc.events.propertyChanged.disconnect(self._on_prop_change)

    def _on_prop_change(self, dev_label: str, prop: str, value: Any):
        if dev_label == self._device_label:
            pre = self._combo.blockSignals(True)
            self._combo.setCurrentText(value)
            self._combo.blockSignals(pre)

    def _refresh_combo(self):
        pre = self._combo.blockSignals(True)
        self._combo.clear()
        self._combo.addItems(self.stateLabels())
        self._combo.blockSignals(pre)

    def state(self) -> int:
        return self._mmc.getState(self._device_label)

    def data(self):
        return self._mmc.getData(self._device_label)

    def stateLabel(self) -> str:
        return self._mmc.getStateLabel(self._device_label)

    def stateLabels(self) -> Tuple[str]:
        return self._mmc.getStateLabels(self._device_label)
