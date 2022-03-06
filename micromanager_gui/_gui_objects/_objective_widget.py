from typing import Optional, Union

from pymmcore_plus import DeviceType
from qtpy.QtWidgets import QComboBox, QHBoxLayout, QLabel, QSizePolicy, QWidget

from .. import _core
from .._core_widgets import StateDeviceWidget
from .._util import ComboMessageBox


class MMObjectivesWidget(QWidget):
    """Objective selector widget.

    Parameters
    ----------
    objective_device : Optional[str]
        Device label for the objective device, by default will be guessed using
        `mmc.guessObjectiveDevices`, and a dialog will be presented if there are
        multiples
    parent : Optional[QWidget]
        Optional parent widget, by default None
    """

    def __init__(self, objective_device: str = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._mmc = _core.get_core_singleton()
        self._objective_device = objective_device or self._guess_objective_device()
        self._combo = self._create_objective_combo(objective_device)

        lbl = QLabel("Objectives:")
        lbl.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)

        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(lbl)
        self.layout().addWidget(self._combo)

        self._mmc.events.systemConfigurationLoaded.connect(self._on_sys_cfg_loaded)
        self.destroyed.connect(self._disconnect_from_core)
        self._on_sys_cfg_loaded()

    def _disconnect_from_core(self):
        self._mmc.events.systemConfigurationLoaded.disconnect(self._on_sys_cfg_loaded)

    def _on_sys_cfg_loaded(self):
        loaded = self._mmc.getLoadedDevices()
        if self._objective_device not in loaded:
            self._objective_device = None
        if len(loaded) > 1:
            if not self._objective_device:
                self._objective_device = self._guess_objective_device()
            self._clear_previous_device_widget()
            self._combo = self._create_objective_combo(self._objective_device)
            self.layout().addWidget(self._combo)

    def _guess_objective_device(self) -> Optional[str]:
        """Try to update the list of objective choices

        1. get a list of potential objective devices from pymmcore
        2. if there is only one, use it, if there are >1, show a dialog box
        """
        state_devs = []
        for d in self._mmc.guessObjectiveDevices():
            try:
                if self._mmc.getDeviceType(d) is DeviceType.StateDevice:
                    state_devs.append(d)
            except RuntimeError:
                continue

        if len(state_devs) == 1:
            return state_devs[0]
        elif state_devs:
            # if obj_devs has more than 1 possible objective device,
            # present dialog to pick one
            dialog = ComboMessageBox(state_devs, "Select Objective Device:", self)
            if dialog.exec_() == dialog.DialogCode.Accepted:
                return dialog.currentText()
        return None

    def _clear_previous_device_widget(self):
        self._combo.setParent(None)
        self._combo.deleteLater()

    def _create_objective_combo(
        self, device_label
    ) -> Union[StateDeviceWidget, QComboBox]:
        if device_label:
            combo = _ObjectiveStateWidget(device_label)
            combo.setMinimumWidth(285)
        else:
            combo = QComboBox()
            combo.setEnabled(False)
        return combo


class _ObjectiveStateWidget(StateDeviceWidget):
    # This logic tries to makes it so that that objective drops before changing...
    # It should be made clear, however, that this *ONLY* works when one controls the
    # objective through the widget, and not if one directly controls it through core

    # TODO: this should be a preference, not a requirement.

    def _drop_focus_motor(self) -> float:
        zdev = self._mmc.getFocusDevice()
        currentZ = self._mmc.getZPosition()
        self._mmc.setPosition(zdev, 0)
        self._mmc.waitForDevice(zdev)
        return currentZ

    def _raise_focus_motor(self, value: float):
        self._mmc.waitForDevice(self._objective_device)
        zdev = self._mmc.getFocusDevice()
        self._mmc.setPosition(zdev, value)
        self._mmc.waitForDevice(zdev)
