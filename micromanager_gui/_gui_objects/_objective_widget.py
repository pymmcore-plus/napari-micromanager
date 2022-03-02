from typing import Optional

from pymmcore_plus import DeviceType
from qtpy import QtWidgets as QtW

from .. import _core
from .._util import ComboMessageBox, blockSignals


class MMObjectivesWidget(QtW.QWidget):
    """Objective selector widget."""

    def __init__(self, parent: Optional[QtW.QWidget] = None):
        super().__init__(parent)
        self._using_config_group = False

        self.combo = QtW.QComboBox()
        self.combo.setMinimumWidth(285)
        self.combo.currentTextChanged.connect(self._set_objective)

        obj_label = QtW.QLabel(text="Objectives:")
        max_policy = QtW.QSizePolicy.Policy.Maximum
        obj_label.setSizePolicy(max_policy, max_policy)

        self.setLayout(QtW.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(obj_label)
        self.layout().addWidget(self.combo)

        self._mmc = _core.get_core_singleton()
        self._connect_to_core()
        self.destroyed.connect(self._disconnect_from_core)

    def _connect_to_core(self):
        self._mmc.events.systemConfigurationLoaded.connect(self._on_sys_cfg_loaded)

    def _disconnect_from_core(self):
        self._mmc.events.systemConfigurationLoaded.disconnect(self._on_sys_cfg_loaded)

    def _on_sys_cfg_loaded(self):
        if len(self._mmc.getLoadedDevices()) > 1:
            self._refresh_objective_choices()

    def _refresh_objective_choices(self, exclude=()):
        """Try to update the list of objective choices

        1. get a list of potential objective devices from pymmcore
        2. if there is only one, use it, if there are >1, show a dialog box
        3. try to _set_objective_choices_from_device_label with the chosen device label.
        4. if it fails, and there were multiple options, recurse, omitting the ones
           that already failed.
        """
        obj_devs = [i for i in self._mmc.guessObjectiveDevices() if i not in exclude]
        if not obj_devs:
            return

        if len(obj_devs) == 1:
            dev = obj_devs[0]
        else:
            # if obj_devs has more than 1 possible objective device,
            # you can select the correct one through a combobox
            dialog = ComboMessageBox(obj_devs, "Select Objective Device:", self)
            if dialog.exec_() == dialog.DialogCode.Accepted:
                dev = dialog.currentText()
            else:
                return

        try:
            self._set_objective_choices_from_device_label(dev)
        except RuntimeError:
            self._refresh_objective_choices(exclude=tuple(exclude) + (dev,))

    def _set_objective_choices_from_device_label(self, dev_label: str):
        if groups := _core.get_cfg_groups_with_device_label(dev_label, max_results=1):
            cfg = groups[0]
            choices = self._mmc.getAvailableConfigs(cfg)
            current = self._mmc.getCurrentConfig(cfg)
            _core.STATE.objectives_cfg = cfg
            self._using_config_group = True
        elif self._mmc.getDeviceType(dev_label) is DeviceType.StateDevice:
            choices = self._mmc.getStateLabels(dev_label)
            current = choices[self._mmc.getState(dev_label)]
            self._using_config_group = False
        else:
            return

        _core.STATE.objective_device = dev_label
        with blockSignals(self.combo):
            self.combo.clear()
            self.combo.addItems(choices)
            self.combo.setCurrentText(current)
        # self.cam_wdg._update_pixel_size()  # TODO

    def _set_objective(self, new_obj: str):
        if not new_obj or not _core.STATE.objective_device:
            return
        mmc = _core.get_core_singleton()
        zdev = mmc.getFocusDevice()
        currentZ = mmc.getZPosition()
        mmc.setPosition(zdev, 0)
        mmc.waitForDevice(zdev)

        if self._using_config_group:
            mmc.setConfig(_core.STATE.objectives_cfg, new_obj)
        else:
            mmc.setProperty(_core.STATE.objective_device, "Label", new_obj)

        mmc.waitForDevice(_core.STATE.objective_device)
        mmc.setPosition(zdev, currentZ)
        mmc.waitForDevice(zdev)

        # self.cam_wdg._update_pixel_size() # TODO: put pixel size on STATE
