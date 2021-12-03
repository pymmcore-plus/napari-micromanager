from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import napari
import numpy as np
from loguru import logger
from pymmcore_plus import CMMCorePlus, DeviceType, RemoteMMCore
from qtpy import QtWidgets as QtW
from qtpy import uic
from qtpy.QtCore import QSize, QTimer
from qtpy.QtGui import QColor, QIcon

from ._illumination import IlluminationDialog
from ._saving import save_sequence
from ._util import (
    AutofocusDevice,
    SelectDeviceFromCombobox,
    blockSignals,
    event_indices,
    extend_array_for_index,
)
from .explore_sample import ExploreSample
from .multid_widget import MultiDWidget, SequenceMeta
from .prop_browser import PropBrowser

if TYPE_CHECKING:
    import napari.layers
    import napari.viewer
    import useq


ICONS = Path(__file__).parent / "icons"
CAM_ICON = QIcon(str(ICONS / "vcam.svg"))
CAM_STOP_ICON = QIcon(str(ICONS / "cam_stop.svg"))

OBJECTIVE = "Objective"
# OBJECTIVE = "TINosePiece"


class _MainUI:
    UI_FILE = str(Path(__file__).parent / "_ui" / "micromanager_gui.ui")

    # The UI_FILE above contains these objects:
    cfg_LineEdit: QtW.QLineEdit
    browse_cfg_Button: QtW.QPushButton
    load_cfg_Button: QtW.QPushButton
    objective_groupBox: QtW.QGroupBox
    objective_comboBox: QtW.QComboBox
    camera_groupBox: QtW.QGroupBox
    bin_comboBox: QtW.QComboBox
    bit_comboBox: QtW.QComboBox
    position_groupBox: QtW.QGroupBox
    x_lineEdit: QtW.QLineEdit
    y_lineEdit: QtW.QLineEdit
    z_lineEdit: QtW.QLineEdit
    stage_groupBox: QtW.QGroupBox
    XY_groupBox: QtW.QGroupBox
    xy_device_comboBox: QtW.QComboBox

    Z_groupBox: QtW.QGroupBox
    focus_device_comboBox: QtW.QComboBox
    up_Button: QtW.QPushButton
    down_Button: QtW.QPushButton
    z_step_size_doubleSpinBox: QtW.QDoubleSpinBox

    offset_Z_groupBox: QtW.QGroupBox
    offset_device_comboBox: QtW.QComboBox
    offset_up_Button: QtW.QPushButton
    offset_down_Button: QtW.QPushButton
    offset_z_step_size_doubleSpinBox: QtW.QDoubleSpinBox

    offset_snap_on_click_z_checkBox: QtW.QCheckBox

    left_Button: QtW.QPushButton
    right_Button: QtW.QPushButton
    y_up_Button: QtW.QPushButton
    y_down_Button: QtW.QPushButton
    xy_step_size_SpinBox: QtW.QSpinBox
    tabWidget: QtW.QTabWidget
    snap_live_tab: QtW.QWidget
    multid_tab: QtW.QWidget
    snap_channel_groupBox: QtW.QGroupBox
    snap_channel_comboBox: QtW.QComboBox
    exp_spinBox: QtW.QDoubleSpinBox
    snap_Button: QtW.QPushButton
    live_Button: QtW.QPushButton
    max_min_val_label: QtW.QLabel
    px_size_doubleSpinBox: QtW.QDoubleSpinBox
    properties_Button: QtW.QPushButton
    illumination_Button: QtW.QPushButton
    snap_on_click_checkBox: QtW.QCheckBox

    def setup_ui(self):
        uic.loadUi(self.UI_FILE, self)  # load QtDesigner .ui file

        # set some defaults
        self.cfg_LineEdit.setText("demo")

        # button icons
        for attr, icon in [
            ("left_Button", "left_arrow_1_green.svg"),
            ("right_Button", "right_arrow_1_green.svg"),
            ("y_up_Button", "up_arrow_1_green.svg"),
            ("y_down_Button", "down_arrow_1_green.svg"),
            ("up_Button", "up_arrow_1_green.svg"),
            ("down_Button", "down_arrow_1_green.svg"),
            ("offset_up_Button", "up_arrow_1_green.svg"),
            ("offset_down_Button", "down_arrow_1_green.svg"),
            ("snap_Button", "cam.svg"),
            ("live_Button", "vcam.svg"),
        ]:
            btn = getattr(self, attr)
            btn.setIcon(QIcon(str(ICONS / icon)))
            btn.setIconSize(QSize(30, 30))


class MainWindow(QtW.QWidget, _MainUI):
    def __init__(self, viewer: napari.viewer.Viewer, remote=True):
        super().__init__()
        self.setup_ui()

        self.viewer = viewer
        self.streaming_timer = None
        self.available_focus_devs = []

        self.objectives_device = None
        self.objectives_cfg = None

        self.autofocus_z_stage = None

        # create connection to mmcore server or process-local variant
        self._mmc = RemoteMMCore() if remote else CMMCorePlus()

        # tab widgets
        self.mda = MultiDWidget(self._mmc)
        self.explorer = ExploreSample(self.viewer, self._mmc)
        self.tabWidget.addTab(self.mda, "Multi-D Acquisition")
        self.tabWidget.addTab(self.explorer, "Sample Explorer")

        # connect mmcore signals
        sig = self._mmc.events

        # note: don't use lambdas with closures on `self`, since the connection
        # to core may outlive the lifetime of this particular widget.
        sig.sequenceStarted.connect(self._on_mda_started)
        sig.sequenceFinished.connect(self._on_mda_finished)
        sig.systemConfigurationLoaded.connect(self._refresh_options)
        sig.XYStagePositionChanged.connect(self._on_xy_stage_position_changed)
        sig.stagePositionChanged.connect(self._on_stage_position_changed)
        sig.exposureChanged.connect(self._on_exp_change)
        sig.frameReady.connect(self._on_mda_frame)
        sig.channelGroupChanged.connect(self._refresh_channel_list)
        sig.configSet.connect(self._on_config_set)
        sig.propertyChanged.connect(self._on_offset_status_changed)

        # connect buttons
        self.load_cfg_Button.clicked.connect(self.load_cfg)
        self.browse_cfg_Button.clicked.connect(self.browse_cfg)
        self.left_Button.clicked.connect(self.stage_x_left)
        self.right_Button.clicked.connect(self.stage_x_right)
        self.y_up_Button.clicked.connect(self.stage_y_up)
        self.y_down_Button.clicked.connect(self.stage_y_down)
        self.up_Button.clicked.connect(self.stage_z_up)
        self.down_Button.clicked.connect(self.stage_z_down)

        # offset
        self.offset_up_Button.clicked.connect(self.offset_up)
        self.offset_down_Button.clicked.connect(self.offset_down)

        self.snap_Button.clicked.connect(self.snap)
        self.live_Button.clicked.connect(self.toggle_live)

        self.illumination_Button.clicked.connect(self.illumination)
        self.properties_Button.clicked.connect(self._show_prop_browser)

        # connect comboBox
        self.objective_comboBox.currentIndexChanged.connect(self.change_objective)
        self.bit_comboBox.currentIndexChanged.connect(self.bit_changed)
        self.bin_comboBox.currentIndexChanged.connect(self.bin_changed)
        self.snap_channel_comboBox.currentTextChanged.connect(self._channel_changed)
        self.focus_device_comboBox.currentTextChanged.connect(self._set_focus_device)
        self.offset_device_comboBox.currentTextChanged.connect(
            self._set_autofocus_device
        )

        # connect spinboxes
        self.exp_spinBox.valueChanged.connect(self._update_exp)
        self.exp_spinBox.setKeyboardTracking(False)

        # refresh options in case a config is already loaded by another remote
        self._refresh_options()

        self.viewer.layers.events.connect(self.update_max_min)
        self.viewer.layers.selection.events.active.connect(self.update_max_min)
        self.viewer.dims.events.current_step.connect(self.update_max_min)

        @sig.pixelSizeChanged.connect
        def _on_px_size_changed(value):
            logger.debug(
                f"\ncurrent pixel config: "
                f"{self._mmc.getCurrentPixelSizeConfig()} \npixel size: {value}"
            )

        @sig.configSet.connect
        def _on_cfg_set(group: str, preset: str):
            print(f"New group cfg set: {group} -> {preset}")

    def illumination(self):
        if not hasattr(self, "_illumination"):
            self._illumination = IlluminationDialog(self._mmc, self)
        self._illumination.show()

    def _show_prop_browser(self):
        pb = PropBrowser(self._mmc, self)
        pb.exec()

    def _on_config_set(self, groupName: str, configName: str):
        if groupName == self._mmc.getOrGuessChannelGroup():
            with blockSignals(self.snap_channel_comboBox):
                self.snap_channel_comboBox.setCurrentText(configName)

    def _set_enabled(self, enabled):
        self.objective_groupBox.setEnabled(enabled)
        self.camera_groupBox.setEnabled(enabled)
        self.XY_groupBox.setEnabled(enabled)
        self.snap_live_tab.setEnabled(enabled)
        self.snap_live_tab.setEnabled(enabled)
        self.Z_groupBox.setEnabled(enabled)

    def _update_exp(self, exposure: float):
        self._mmc.setExposure(exposure)
        if self.streaming_timer:
            self.streaming_timer.setInterval(int(exposure))
            self._mmc.stopSequenceAcquisition()
            self._mmc.startContinuousSequenceAcquisition(exposure)

    def _on_exp_change(self, camera: str, exposure: float):
        with blockSignals(self.exp_spinBox):
            self.exp_spinBox.setValue(exposure)
        if self.streaming_timer:
            self.streaming_timer.setInterval(int(exposure))

    def _on_mda_started(self, sequence: useq.MDASequence):
        """ "create temp folder and block gui when mda starts."""
        self._set_enabled(False)

    def _on_mda_frame(self, image: np.ndarray, event: useq.MDAEvent):
        meta = self.mda.SEQUENCE_META.get(event.sequence) or SequenceMeta()

        if meta.mode != "mda":
            return

        # pick layer name
        file_name = meta.file_name if meta.should_save else "Exp"
        channelstr = (
            f"[{event.channel.config}_idx{event.index['c']}]_"
            if meta.split_channels
            else ""
        )
        layer_name = f"{file_name}_{channelstr}{event.sequence.uid}"

        try:  # see if we already have a layer with this sequence
            layer = self.viewer.layers[layer_name]

            # get indices of new image
            im_idx = tuple(
                event.index[k]
                for k in event_indices(event)
                if not (meta.split_channels and k == "c")
            )

            # make sure array shape contains im_idx, or pad with zeros
            new_array = extend_array_for_index(layer.data, im_idx)
            # add the incoming index at the appropriate index
            new_array[im_idx] = image
            # set layer data
            layer.data = new_array
            for a, v in enumerate(im_idx):
                self.viewer.dims.set_point(a, v)

        except KeyError:  # add the new layer to the viewer
            seq = event.sequence
            _image = image[(np.newaxis,) * len(seq.shape)]
            layer = self.viewer.add_image(_image, name=layer_name, blending="additive")

            # dimensions labels
            labels = [i for i in seq.axis_order if i in event.index] + ["y", "x"]
            self.viewer.dims.axis_labels = labels

            # add metadata to layer
            layer.metadata["useq_sequence"] = seq
            layer.metadata["uid"] = seq.uid
            # storing event.index in addition to channel.config because it's
            # possible to have two of the same channel in one sequence.
            layer.metadata["ch_id"] = f'{event.channel.config}_idx{event.index["c"]}'

    def _on_mda_finished(self, sequence: useq.MDASequence):
        """Save layer and add increment to save name."""
        meta = self.mda.SEQUENCE_META.pop(sequence, SequenceMeta())
        save_sequence(sequence, self.viewer.layers, meta)
        # reactivate gui when mda finishes.
        self._set_enabled(True)

    def browse_cfg(self):
        self._mmc.unloadAllDevices()  # unload all devicies
        print(f"Loaded Devices: {self._mmc.getLoadedDevices()}")

        # clear spinbox/combobox without accidently setting properties
        boxes = [
            self.objective_comboBox,
            self.bin_comboBox,
            self.bit_comboBox,
            self.snap_channel_comboBox,
            self.xy_device_comboBox,
            self.focus_device_comboBox,
            self.offset_device_comboBox,
        ]
        with blockSignals(boxes):
            for box in boxes:
                box.clear()

        self.mda.clear_channel()
        self.mda.clear_positions()
        self.explorer.clear_channel()
        self.objectives_device = None
        self.objectives_cfg = None

        file_dir = QtW.QFileDialog.getOpenFileName(self, "", "⁩", "cfg(*.cfg)")
        self.cfg_LineEdit.setText(str(file_dir[0]))
        self.max_min_val_label.setText("None")
        self.load_cfg_Button.setEnabled(True)

    def load_cfg(self):
        self.load_cfg_Button.setEnabled(False)
        print("loading", self.cfg_LineEdit.text())
        self._mmc.loadSystemConfiguration(self.cfg_LineEdit.text())

    def _refresh_options(self):
        self._refresh_camera_options()
        self._refresh_objective_options()
        self._refresh_channel_list()
        self._refresh_positions()
        self._refresh_xyz_devices()

    def _refresh_camera_options(self):
        cam_device = self._mmc.getCameraDevice()
        if not cam_device:
            return
        cam_props = self._mmc.getDevicePropertyNames(cam_device)
        if "Binning" in cam_props:
            bin_opts = self._mmc.getAllowedPropertyValues(cam_device, "Binning")
            with blockSignals(self.bin_comboBox):
                self.bin_comboBox.clear()
                self.bin_comboBox.addItems(bin_opts)
                self.bin_comboBox.setCurrentText(
                    self._mmc.getProperty(cam_device, "Binning")
                )

        if "PixelType" in cam_props:
            px_t = self._mmc.getAllowedPropertyValues(cam_device, "PixelType")
            with blockSignals(self.bit_comboBox):
                self.bit_comboBox.clear()
                self.bit_comboBox.addItems(px_t)
                self.bit_comboBox.setCurrentText(
                    self._mmc.getProperty(cam_device, "PixelType")
                )

    def _refresh_objective_options(self):

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
            current_cfg = self._mmc.getCurrentConfig(obj_dev)
        else:
            current_cfg = self._mmc.getState(obj_dev)
            presets = self._mmc.getStateLabels(obj_dev)
        self._add_objective_to_gui(current_cfg, presets)

    def _get_objective_device(self, obj_device: str):
        # check if there is a configuration group for the objectives
        for cfg_groups in self._mmc.getAvailableConfigGroups():
            # e.g. ('Camera', 'Channel', 'Objectives')

            presets = self._mmc.getAvailableConfigs(cfg_groups)

            if not presets:
                continue

            cfg_data = self._mmc.getConfigData(
                cfg_groups, presets[0]
            )  # first group option e.g. TINosePiece: State=1

            device = cfg_data.getSetting(0).getDeviceLabel()
            # e.g. TINosePiece

            if device == obj_device:
                self.objectives_device = device
                self.objectives_cfg = cfg_groups
                return self.objectives_device, self.objectives_cfg, presets

        self.objectives_device = obj_device
        return self.objectives_device, None, None

    def _add_objective_to_gui(self, current_cfg, presets):
        with blockSignals(self.objective_comboBox):
            self.objective_comboBox.clear()
            self.objective_comboBox.addItems(presets)
            if isinstance(current_cfg, int):
                self.objective_comboBox.setCurrentIndex(current_cfg)
            else:
                self.objective_comboBox.setCurrentText(current_cfg)
            self._update_pixel_size()
            return

    def _update_pixel_size(self):
        # if pixel size is already set -> return
        if bool(self._mmc.getCurrentPixelSizeConfig()):
            return
        # if not, create and store a new pixel size config for the current objective.
        curr_obj = self._mmc.getProperty(self.objectives_device, "Label")
        # get magnification info from the current objective label
        match = re.search(r"(\d{1,3})[xX]", curr_obj)
        if match:
            mag = int(match.groups()[0])
            image_pixel_size = self.px_size_doubleSpinBox.value() / mag
            px_cgf_name = f"px_size_{curr_obj}"
            # set image pixel sixe (x,y) for the newly created pixel size config
            self._mmc.definePixelSizeConfig(
                px_cgf_name, self.objectives_device, "Label", curr_obj
            )
            self._mmc.setPixelSizeUm(px_cgf_name, image_pixel_size)
            self._mmc.setPixelSizeConfig(px_cgf_name)
        # if it does't match, px size is set to 0.0

    def _refresh_channel_list(self):
        guessed_channel_list = self._mmc.getOrGuessChannelGroup()

        if not guessed_channel_list:
            return

        if len(guessed_channel_list) == 1:
            self._set_channel_group(guessed_channel_list[0])
        else:
            # if guessed_channel_list has more than 1 possible channel group,
            # you can select the correct one through a combobox
            ch = SelectDeviceFromCombobox(
                guessed_channel_list,
                "Select Channel Group:",
                self,
            )
            ch.val_changed.connect(self._set_channel_group)
            ch.show()

    def _set_channel_group(self, guessed_channel: str):
        channel_group = guessed_channel
        self._mmc.setChannelGroup(channel_group)
        channel_list = self._mmc.getAvailableConfigs(channel_group)
        with blockSignals(self.snap_channel_comboBox):
            self.snap_channel_comboBox.clear()
            self.snap_channel_comboBox.addItems(channel_list)
            self.snap_channel_comboBox.setCurrentText(
                self._mmc.getCurrentConfig(channel_group)
            )

    def _refresh_positions(self):
        if self._mmc.getXYStageDevice():
            x, y = self._mmc.getXPosition(), self._mmc.getYPosition()
            self._on_xy_stage_position_changed(self._mmc.getXYStageDevice(), x, y)
        if self._mmc.getFocusDevice():
            self.z_lineEdit.setText(f"{self._mmc.getZPosition():.1f}")

    def _refresh_xyz_devices(self):
        self.focus_device_comboBox.clear()
        self.offset_device_comboBox.clear()
        self.xy_device_comboBox.clear()

        xy_stage_dev = [
            dev for dev in self._mmc.getLoadedDevicesOfType(DeviceType.XYStageDevice)
        ]

        focus_devs = [
            dev
            for dev in self._mmc.getLoadedDevicesOfType(DeviceType.StageDevice)
            if dev != "TIPFSOffset"  # to remove Nikon TIPFSOffset from the list
        ]

        offset_devs = [
            dev for dev in self._mmc.getLoadedDevicesOfType(DeviceType.AutoFocusDevice)
        ]

        if not xy_stage_dev:
            self.xy_device_comboBox.setEnabled(False)
        else:
            self.xy_device_comboBox.addItems(xy_stage_dev)
            self._set_xy_stage_device()

        if not focus_devs:
            self.focus_device_comboBox.setEnabled(False)
        else:
            self.focus_device_comboBox.addItems(focus_devs)
            self._set_focus_device()

        if not offset_devs:
            self.offset_device_comboBox.setEnabled(False)
        else:
            self.offset_device_comboBox.addItems(offset_devs)
            self._set_autofocus_device()

    def _set_xy_stage_device(self):
        if not self.xy_device_comboBox.count():
            return
        self._mmc.setXYStageDevice(self.xy_device_comboBox.currentText())

    def _set_focus_device(self):
        if not self.focus_device_comboBox.count():
            return
        self._mmc.setFocusDevice(self.focus_device_comboBox.currentText())

    def _set_autofocus_device(self):
        if not self.offset_device_comboBox.count():
            return
        self.autofocus_z_stage = AutofocusDevice.create(
            self.offset_device_comboBox.currentText()
        )
        self._mmc.setAutoFocusDevice(self.autofocus_z_stage)

    def bit_changed(self):
        if self.bit_comboBox.count() > 0:
            bits = self.bit_comboBox.currentText()
            self._mmc.setProperty(self._mmc.getCameraDevice(), "PixelType", bits)

    def bin_changed(self):
        if self.bin_comboBox.count() > 0:
            bins = self.bin_comboBox.currentText()
            cd = self._mmc.getCameraDevice()
            self._mmc.setProperty(cd, "Binning", bins)

    def _channel_changed(self, newChannel: str):
        self._mmc.setConfig(self._mmc.getChannelGroup(), newChannel)

    def _on_xy_stage_position_changed(self, name, x, y):
        self.x_lineEdit.setText(f"{x:.1f}")
        self.y_lineEdit.setText(f"{y:.1f}")

    def _on_stage_position_changed(self, name, value):
        if "z" in name.lower():  # hack
            self.z_lineEdit.setText(f"{value:.1f}")

    def stage_x_left(self):
        self._mmc.setRelativeXYPosition(-float(self.xy_step_size_SpinBox.value()), 0.0)
        if self.snap_on_click_checkBox.isChecked():
            self.snap()

    def stage_x_right(self):
        self._mmc.setRelativeXYPosition(float(self.xy_step_size_SpinBox.value()), 0.0)
        if self.snap_on_click_checkBox.isChecked():
            self.snap()

    def stage_y_up(self):
        self._mmc.setRelativeXYPosition(
            0.0,
            float(self.xy_step_size_SpinBox.value()),
        )
        if self.snap_on_click_checkBox.isChecked():
            self.snap()

    def stage_y_down(self):
        self._mmc.setRelativeXYPosition(
            0.0,
            -float(self.xy_step_size_SpinBox.value()),
        )
        if self.snap_on_click_checkBox.isChecked():
            self.snap()

    def stage_z_up(self):
        self._mmc.setRelativeXYZPosition(
            0.0, 0.0, float(self.z_step_size_doubleSpinBox.value())
        )
        if self.snap_on_click_checkBox.isChecked():
            self.snap()

    def stage_z_down(self):
        self._mmc.setRelativeXYZPosition(
            0.0, 0.0, -float(self.z_step_size_doubleSpinBox.value())
        )
        if self.snap_on_click_checkBox.isChecked():
            self.snap()

    def _on_offset_status_changed(self):

        if self.autofocus_z_stage:

            if self.autofocus_z_stage.isEngaged():
                if (
                    self.autofocus_z_stage.isLocked()
                    or self.autofocus_z_stage.isFocusing()
                ):
                    self.offset_Z_groupBox.setEnabled(True)
                    self.Z_groupBox.setEnabled(False)

            else:
                self.offset_Z_groupBox.setEnabled(False)
                self.Z_groupBox.setEnabled(True)

    def offset_up(self):
        if self._mmc.isContinuousFocusLocked():
            current_offset = float(
                self._mmc.getProperty(self.autofocus_z_stage, "Position")
            )
            new_offset = current_offset + float(
                self.offset_z_step_size_doubleSpinBox.value()
            )
            self.autofocus_z_stage.set_offset(new_offset)
            if self.snap_on_click_checkBox.isChecked():
                self.snap()

    def offset_down(self):
        if self._mmc.isContinuousFocusLocked():
            current_offset = float(
                self._mmc.getProperty(self.autofocus_z_stage, "Position")
            )
            new_offset = current_offset - float(
                self.offset_z_step_size_doubleSpinBox.value()
            )
            self.autofocus_z_stage.set_offset(new_offset)
            if self.snap_on_click_checkBox.isChecked():
                self.snap()

    def change_objective(self):
        if self.objective_comboBox.count() <= 0:
            return

        if self.objectives_device == "":
            return

        zdev = self._mmc.getFocusDevice()

        currentZ = self._mmc.getZPosition()
        self._mmc.setPosition(zdev, 0)
        self._mmc.waitForDevice(zdev)

        try:
            self._mmc.setConfig(
                self.objectives_cfg, self.objective_comboBox.currentText()
            )
        except ValueError:
            self._mmc.setProperty(
                self.objectives_device, "Label", self.objective_comboBox.currentText()
            )

        self._mmc.waitForDevice(self.objectives_device)
        self._mmc.setPosition(zdev, currentZ)
        self._mmc.waitForDevice(zdev)

        self._update_pixel_size()

    def update_viewer(self, data=None):
        # TODO: - fix the fact that when you change the objective
        #         the image translation is wrong
        #       - are max and min_val_lineEdit updating in live mode?
        if data is None:
            try:
                data = self._mmc.getLastImage()
            except (RuntimeError, IndexError):
                # circular buffer empty
                return
        try:
            preview_layer = self.viewer.layers["preview"]
            preview_layer.data = data
        except KeyError:
            preview_layer = self.viewer.add_image(data, name="preview")

        self.update_max_min()

        if self.streaming_timer is None:
            self.viewer.reset_view()

    def update_max_min(self, event=None):

        if self.tabWidget.currentIndex() != 0:
            return

        min_max_txt = ""

        for layer in self.viewer.layers.selection:

            if isinstance(layer, napari.layers.Image) and layer.visible:

                col = layer.colormap.name

                if col not in QColor.colorNames():
                    col = "gray"

                # min and max of current slice
                min_max_show = tuple(layer._calc_data_range(mode="slice"))
                min_max_txt += f'<font color="{col}">{min_max_show}</font>'

        self.max_min_val_label.setText(min_max_txt)

    def snap(self):
        self.stop_live()
        self._mmc.snapImage()
        self.update_viewer(self._mmc.getImage())

    def start_live(self):
        self._mmc.startContinuousSequenceAcquisition(self.exp_spinBox.value())
        self.streaming_timer = QTimer()
        self.streaming_timer.timeout.connect(self.update_viewer)
        self.streaming_timer.start(int(self.exp_spinBox.value()))
        self.live_Button.setText("Stop")

    def stop_live(self):
        self._mmc.stopSequenceAcquisition()
        if self.streaming_timer is not None:
            self.streaming_timer.stop()
            self.streaming_timer = None
        self.live_Button.setText("Live")
        self.live_Button.setIcon(CAM_ICON)

    def toggle_live(self, event=None):
        if self.streaming_timer is None:

            ch_group = self._mmc.getOrGuessChannelGroup()
            self._mmc.setConfig(ch_group, self.snap_channel_comboBox.currentText())

            self.start_live()
            self.live_Button.setIcon(CAM_STOP_ICON)
        else:
            self.stop_live()
            self.live_Button.setIcon(CAM_ICON)
