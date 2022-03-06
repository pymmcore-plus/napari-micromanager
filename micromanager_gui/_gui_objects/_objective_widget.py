from typing import Optional

from pymmcore_plus import DeviceType
from qtpy import QtWidgets as QtW

from .. import _core
from .._core_widgets import DeviceWidget
from .._util import ComboMessageBox


class MMObjectivesWidget(QtW.QWidget):
    """Objective selector widget."""

    def __init__(
        self, objective_device: str = None, parent: Optional[QtW.QWidget] = None
    ):
        super().__init__(parent)
        self._objective_device = objective_device

        obj_label = QtW.QLabel("Objectives:")
        max_policy = QtW.QSizePolicy.Policy.Maximum
        obj_label.setSizePolicy(max_policy, max_policy)
        self.combo = QtW.QComboBox()  # just an empty stub. real one in create_obj_combo
        self.combo.setEnabled(False)
        self.setLayout(QtW.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(obj_label)
        self.layout().addWidget(self.combo)

        self._mmc = _core.get_core_singleton()
        self._mmc.events.systemConfigurationLoaded.connect(self._on_sys_cfg_loaded)
        self.destroyed.connect(self._disconnect_from_core)
        self._on_sys_cfg_loaded()

    def _on_sys_cfg_loaded(self):
        loaded = self._mmc.getLoadedDevices()
        if self._objective_device not in loaded:
            self._objective_device = None
        if len(loaded) > 1:
            if not self._objective_device:
                self._objective_device = self._guess_objective_device()
            self._clear_previous_device_widget()
            if self._objective_device:
                self._create_objective_combo()
            else:
                self.combo = QtW.QComboBox()

    def _clear_previous_device_widget(self):
        self.combo.setParent(None)
        self.combo.deleteLater()

    def _create_objective_combo(self):
        self._clear_previous_device_widget()
        self.combo = DeviceWidget.for_device(self._objective_device)
        self.combo.setMinimumWidth(285)
        self.layout().addWidget(self.combo)

    def _disconnect_from_core(self):
        self._mmc.events.systemConfigurationLoaded.disconnect(self._on_sys_cfg_loaded)

    def _guess_objective_device(self) -> Optional[str]:
        """Try to update the list of objective choices

        1. get a list of potential objective devices from pymmcore
        2. if there is only one, use it, if there are >1, show a dialog box
        3. try to _set_objective_choices_from_device_label with the chosen device label.
        4. if it fails, and there were multiple options, recurse, omitting the ones
           that already failed.
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

    def setValue(self, new_obj: str) -> None:
        if new_obj not in self._mmc.getStateLabels(self._objective_device):
            raise ValueError(f"Invalid objective label: {new_obj!r}")
        current = self._drop_focus_motor()
        self._mmc.setStateLabel(self._objective_device, new_obj)
        self._mmc.waitForDevice(_core.STATE.objective_device)
        self._raise_focus_motor(current)

        # self.cam_wdg._update_pixel_size() # TODO: put pixel size on STATE

    def _drop_focus_motor(self) -> float:
        zdev = self._mmc.getFocusDevice()
        currentZ = self._mmc.getZPosition()
        self._mmc.setPosition(zdev, 0)
        self._mmc.waitForDevice(zdev)
        return currentZ

    def _raise_focus_motor(self, value: float):
        zdev = self._mmc.getFocusDevice()
        self._mmc.setPosition(zdev, value)
        self._mmc.waitForDevice(zdev)
