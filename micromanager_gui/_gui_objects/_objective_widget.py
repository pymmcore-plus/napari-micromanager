from typing import Optional

from qtpy import QtWidgets as QtW

from .. import _core
from .._util import SelectDeviceFromCombobox, blockSignals


class MMObjectivesWidget(QtW.QWidget):
    """Objective selector widget."""

    def __init__(self, parent: Optional[QtW.QWidget] = None):
        super().__init__(parent)

        self.combo = QtW.QComboBox()
        self.combo.setMinimumWidth(285)
        self.combo.currentTextChanged.connect(self._change_objective)

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
            self._refresh_options()

    # objectives
    def _refresh_options(self):

        obj_dev_list = self._mmc.guessObjectiveDevices()
        # e.g. ['TiNosePiece']

        if not obj_dev_list:
            return

        if len(obj_dev_list) == 1:
            self._set_objectives(obj_dev_list[0])
        else:
            # if obj_dev_list has more than 1 possible objective device,
            # you can select the correct one through a combobox
            obj = SelectDeviceFromCombobox(
                obj_dev_list,
                "Select Objective Device:",
                self,
            )
            obj.val_changed.connect(self._set_objectives)
            obj.show()

    def _set_objectives(self, obj_device: str):

        obj_dev, obj_cfg, presets = self._get_objective_device(obj_device)

        if obj_dev and obj_cfg and presets:
            current_obj = self._mmc.getCurrentConfig(obj_cfg)
        else:
            current_obj = self._mmc.getState(obj_dev)
            presets = self._mmc.getStateLabels(obj_dev)
        self._add_objective_to_gui(current_obj, presets)

    def _get_objective_device(self, obj_device: str):
        # check if there is a configuration group for the objectives
        for cfg_groups in self._mmc.getAvailableConfigGroups():
            # e.g. ('Camera', 'Channel', 'Objectives')

            presets = self._mmc.getAvailableConfigs(cfg_groups)

            if not presets:
                continue

            # first group option e.g. TINosePiece: State=1
            cfg_data = self._mmc.getConfigData(cfg_groups, presets[0])

            device = cfg_data.getSetting(0).getDeviceLabel()
            # e.g. TINosePiece

            if device == obj_device:
                _core.STATE.objective_device = device
                _core.STATE.objectives_cfg = cfg_groups
                return _core.STATE.objective_device, _core.STATE.objectives_cfg, presets

        _core.STATE.objective_device = obj_device
        return _core.STATE.objective_device, None, None

    def _add_objective_to_gui(self, current_obj, presets):
        with blockSignals(self.combo):
            self.combo.clear()
            self.combo.addItems(presets)
            if isinstance(current_obj, int):
                self.combo.setCurrentIndex(current_obj)
            else:
                self.combo.setCurrentText(current_obj)

            # self.cam_wdg._update_pixel_size()  # TODO

    def _change_objective(self, new_obj: str):
        if not new_obj or not _core.STATE.objective_device:
            return

        mmc = _core.get_core_singleton()
        zdev = mmc.getFocusDevice()
        currentZ = mmc.getZPosition()
        mmc.setPosition(zdev, 0)
        mmc.waitForDevice(zdev)

        try:
            mmc.setConfig(_core.STATE.objectives_cfg, new_obj)
        except ValueError:
            mmc.setProperty(_core.STATE.objective_device, "Label", new_obj)

        mmc.waitForDevice(_core.STATE.objective_device)
        mmc.setPosition(zdev, currentZ)
        mmc.waitForDevice(zdev)

        # self.cam_wdg._update_pixel_size() # TODO: put pixel size on STATE
