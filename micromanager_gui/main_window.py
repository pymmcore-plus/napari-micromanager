from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import napari
import numpy as np
from pymmcore_plus import CMMCorePlus, DeviceType, RemoteMMCore
from pymmcore_plus._util import find_micromanager
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QColor, QIcon
from superqt.utils import create_worker

from ._camera_roi import CameraROI
from ._gui import MicroManagerWidget
from ._illumination import IlluminationDialog
from ._saving import save_sequence
from ._util import (
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


class MainWindow(MicroManagerWidget):
    def __init__(
        self,
        viewer: napari.viewer.Viewer,
        remote=False,
        mmc: CMMCorePlus | RemoteMMCore = None,
    ):

        super().__init__()

        self.viewer = viewer

        self.cfg = self.mm_configuration
        self.obj = self.mm_objectives
        self.ill = self.mm_illumination
        self.cam = self.mm_camera
        self.stages = self.mm_xyz_stages
        self.tab = self.mm_tab

        # create connection to mmcore server or process-local variant
        if mmc is not None:
            self._mmc = mmc
        else:
            self._mmc = RemoteMMCore() if remote else CMMCorePlus.instance()

        adapter_path = find_micromanager()
        if not adapter_path:
            raise RuntimeError(
                "Could not find micromanager adapters. Please run "
                "`python -m pymmcore_plus.install` or install manually and set "
                "MICROMANAGER_PATH."
            )

        # tab widgets
        self.mda = MultiDWidget(self._mmc)
        self.explorer = ExploreSample(self.viewer, self._mmc)

        # add mda and explorer tabs to mm_tab widget
        self.tab.tabWidget.addTab(self.mda, "Multi-D Acquisition")
        self.tab.tabWidget.addTab(self.explorer, "Sample Explorer")

        self.streaming_timer = None
        self.available_focus_devs = []
        self.objectives_device = None
        self.objectives_cfg = None

        # disable gui
        self._set_enabled(False)

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

        # connect buttons
        self.cfg.load_cfg_Button.clicked.connect(self.load_cfg)
        self.cfg.browse_cfg_Button.clicked.connect(self.browse_cfg)
        self.stages.left_Button.clicked.connect(self.stage_x_left)
        self.stages.right_Button.clicked.connect(self.stage_x_right)
        self.stages.y_up_Button.clicked.connect(self.stage_y_up)
        self.stages.y_down_Button.clicked.connect(self.stage_y_down)
        self.stages.up_Button.clicked.connect(self.stage_z_up)
        self.stages.down_Button.clicked.connect(self.stage_z_down)

        self.tab.snap_Button.clicked.connect(self.snap)
        self.tab.live_Button.clicked.connect(self.toggle_live)

        self.ill.illumination_Button.clicked.connect(self.illumination)
        self.cfg.properties_Button.clicked.connect(self._show_prop_browser)

        self.stages.focus_device_comboBox.currentTextChanged.connect(
            self._set_focus_device
        )

        # connect comboBox
        self.obj.objective_comboBox.currentIndexChanged.connect(self.change_objective)
        self.cam.bit_comboBox.currentIndexChanged.connect(self.bit_changed)
        self.cam.bin_comboBox.currentIndexChanged.connect(self.bin_changed)
        self.tab.snap_channel_comboBox.currentTextChanged.connect(self._channel_changed)

        self.cam_roi = CameraROI(
            self.viewer, self._mmc, self.cam.cam_roi_comboBox, self.cam.crop_Button
        )

        # connect spinboxes
        self.tab.exp_spinBox.valueChanged.connect(self._update_exp)
        self.tab.exp_spinBox.setKeyboardTracking(False)

        # refresh options in case a config is already loaded by another remote
        self._refresh_options()

        self.viewer.layers.events.connect(self.update_max_min)
        self.viewer.layers.selection.events.active.connect(self.update_max_min)
        self.viewer.dims.events.current_step.connect(self.update_max_min)

    def _set_enabled(self, enabled):
        if self._mmc.getCameraDevice():
            self.cam.camera_groupBox.setEnabled(enabled)
            self.cam.crop_Button.setEnabled(enabled)
            self.tab.snap_live_tab.setEnabled(enabled)
            self.tab.snap_live_tab.setEnabled(enabled)
        else:
            self.cam.camera_groupBox.setEnabled(False)
            self.cam.crop_Button.setEnabled(False)
            self.tab.snap_live_tab.setEnabled(False)
            self.tab.snap_live_tab.setEnabled(False)

        if self._mmc.getXYStageDevice():
            self.stages.XY_groupBox.setEnabled(enabled)
        else:
            self.stages.XY_groupBox.setEnabled(False)

        if self._mmc.getFocusDevice():
            self.stages.Z_groupBox.setEnabled(enabled)
        else:
            self.stages.Z_groupBox.setEnabled(False)

        self.obj.objective_groupBox.setEnabled(enabled)
        self.ill.illumination_Button.setEnabled(enabled)
        self.tab.tabWidget.setEnabled(enabled)

        self.mda._set_enabled(enabled)
        if self._mmc.getXYStageDevice():
            self.explorer._set_enabled(enabled)
        else:
            self.explorer._set_enabled(False)

    def browse_cfg(self):
        self._mmc.unloadAllDevices()  # unload all devicies

        self._set_enabled(False)

        # clear spinbox/combobox without accidently setting properties
        boxes = [
            self.obj.objective_comboBox,
            self.cam.bin_comboBox,
            self.cam.bit_comboBox,
            self.tab.snap_channel_comboBox,
            self.stages.xy_device_comboBox,
            self.stages.focus_device_comboBox,
        ]
        with blockSignals(boxes):
            for box in boxes:
                box.clear()

        self.mda.clear_channel()
        self.mda.clear_positions()
        self.explorer.clear_channel()

        self.objectives_device = None
        self.objectives_cfg = None

        file_dir = QtW.QFileDialog.getOpenFileName(self, "", "", "cfg(*.cfg)")
        self.cfg.cfg_LineEdit.setText(str(file_dir[0]))
        self.tab.max_min_val_label.setText("None")
        self.cfg.load_cfg_Button.setEnabled(True)

    def load_cfg(self):
        self.cfg.load_cfg_Button.setEnabled(False)
        cfg = self.cfg.cfg_LineEdit.text()
        if cfg == "":
            cfg = "MMConfig_demo.cfg"
            self.cfg.cfg_LineEdit.setText(cfg)
        self._mmc.loadSystemConfiguration(cfg)
        self._refresh_options()
        self._set_enabled(True)

    def _refresh_options(self):
        self._refresh_camera_options()
        self._refresh_objective_options()
        self._refresh_channel_list()
        self._refresh_positions()
        self._refresh_xyz_devices()

    def update_viewer(self, data=None):
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

        if self.tab.tabWidget.currentIndex() != 0:
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

        self.tab.max_min_val_label.setText(min_max_txt)

    def snap(self):
        self.stop_live()

        # snap in a thread so we don't freeze UI when using process local mmc
        create_worker(
            self._mmc.snapImage,
            _connect={"finished": lambda: self.update_viewer(self._mmc.getImage())},
            _start_thread=True,
        )

    def start_live(self):
        self._mmc.startContinuousSequenceAcquisition(self.tab.exp_spinBox.value())
        self.streaming_timer = QTimer()
        self.streaming_timer.timeout.connect(self.update_viewer)
        self.streaming_timer.start(int(self.tab.exp_spinBox.value()))
        self.tab.live_Button.setText("Stop")

    def stop_live(self):
        self._mmc.stopSequenceAcquisition()
        if self.streaming_timer is not None:
            self.streaming_timer.stop()
            self.streaming_timer = None
        self.tab.live_Button.setText("Live")
        self.tab.live_Button.setIcon(CAM_ICON)

    def toggle_live(self, event=None):
        if self.streaming_timer is None:

            ch_group = self._mmc.getChannelGroup()
            if ch_group:
                self._mmc.setConfig(
                    ch_group, self.tab.snap_channel_comboBox.currentText()
                )
            else:
                return

            self.start_live()
            self.tab.live_Button.setIcon(CAM_STOP_ICON)
        else:
            self.stop_live()
            self.tab.live_Button.setIcon(CAM_ICON)

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

    # exposure time
    def _update_exp(self, exposure: float):
        self._mmc.setExposure(exposure)
        if self.streaming_timer:
            self.streaming_timer.setInterval(int(exposure))
            self._mmc.stopSequenceAcquisition()
            self._mmc.startContinuousSequenceAcquisition(exposure)

    def _on_exp_change(self, camera: str, exposure: float):
        with blockSignals(self.tab.exp_spinBox):
            self.tab.exp_spinBox.setValue(exposure)
        if self.streaming_timer:
            self.streaming_timer.setInterval(int(exposure))

    # illumination
    def illumination(self):
        if hasattr(self, "_illumination"):
            self._illumination.close()
        self._illumination = IlluminationDialog(self._mmc, self)
        self._illumination.setWindowFlags(
            Qt.Window
            | Qt.WindowTitleHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowCloseButtonHint
        )
        self._illumination.show()

    # property browser
    def _show_prop_browser(self):
        pb = PropBrowser(self._mmc, self)
        pb.exec()

    # channels
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
        with blockSignals(self.tab.snap_channel_comboBox):
            self.tab.snap_channel_comboBox.clear()
            self.tab.snap_channel_comboBox.addItems(channel_list)
            self.tab.snap_channel_comboBox.setCurrentText(
                self._mmc.getCurrentConfig(channel_group)
            )

    def _on_config_set(self, groupName: str, configName: str):
        if groupName == self._mmc.getOrGuessChannelGroup():
            with blockSignals(self.tab.snap_channel_comboBox):
                self.tab.snap_channel_comboBox.setCurrentText(configName)

    def _channel_changed(self, newChannel: str):
        self._mmc.setConfig(self._mmc.getChannelGroup(), newChannel)

    # objectives
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

    def _add_objective_to_gui(self, current_obj, presets):
        with blockSignals(self.obj.objective_comboBox):
            self.obj.objective_comboBox.clear()
            self.obj.objective_comboBox.addItems(presets)
            if isinstance(current_obj, int):
                self.obj.objective_comboBox.setCurrentIndex(current_obj)
            else:
                self.obj.objective_comboBox.setCurrentText(current_obj)
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

            if self.cam.px_size_doubleSpinBox.value() == 1.0:
                return

            image_pixel_size = self.cam.px_size_doubleSpinBox.value() / mag
            px_cgf_name = f"px_size_{curr_obj}"
            # set image pixel sixe (x,y) for the newly created pixel size config
            self._mmc.definePixelSizeConfig(
                px_cgf_name, self.objectives_device, "Label", curr_obj
            )
            self._mmc.setPixelSizeUm(px_cgf_name, image_pixel_size)
            self._mmc.setPixelSizeConfig(px_cgf_name)
        # if it does't match, px size is set to 0.0

    def change_objective(self):
        if self.obj.objective_comboBox.count() <= 0:
            return

        if self.objectives_device == "":
            return

        zdev = self._mmc.getFocusDevice()

        currentZ = self._mmc.getZPosition()
        self._mmc.setPosition(zdev, 0)
        self._mmc.waitForDevice(zdev)

        try:
            self._mmc.setConfig(
                self.objectives_cfg, self.obj.objective_comboBox.currentText()
            )
        except ValueError:
            self._mmc.setProperty(
                self.objectives_device,
                "Label",
                self.obj.objective_comboBox.currentText(),
            )

        self._mmc.waitForDevice(self.objectives_device)
        self._mmc.setPosition(zdev, currentZ)
        self._mmc.waitForDevice(zdev)

        self._update_pixel_size()

    # stages
    def _refresh_positions(self):
        if self._mmc.getXYStageDevice():
            x, y = self._mmc.getXPosition(), self._mmc.getYPosition()
            self._on_xy_stage_position_changed(self._mmc.getXYStageDevice(), x, y)
        if self._mmc.getFocusDevice():
            self.stages.z_lineEdit.setText(f"{self._mmc.getZPosition():.1f}")

    def _refresh_xyz_devices(self):

        # since there is no offset control yet:
        self.stages.offset_Z_groupBox.setEnabled(False)

        self.stages.focus_device_comboBox.clear()
        self.stages.xy_device_comboBox.clear()

        xy_stage_devs = list(self._mmc.getLoadedDevicesOfType(DeviceType.XYStageDevice))

        focus_devs = list(self._mmc.getLoadedDevicesOfType(DeviceType.StageDevice))

        if not xy_stage_devs:
            self.stages.XY_groupBox.setEnabled(False)
        else:
            self.stages.XY_groupBox.setEnabled(True)
            self.stages.xy_device_comboBox.addItems(xy_stage_devs)
            self._set_xy_stage_device()

        if not focus_devs:
            self.stages.Z_groupBox.setEnabled(False)
        else:
            self.stages.Z_groupBox.setEnabled(True)
            self.stages.focus_device_comboBox.addItems(focus_devs)
            self._set_focus_device()

    def _set_xy_stage_device(self):
        if not self.stages.xy_device_comboBox.count():
            return
        self._mmc.setXYStageDevice(self.stages.xy_device_comboBox.currentText())

    def _set_focus_device(self):
        if not self.stages.focus_device_comboBox.count():
            return
        self._mmc.setFocusDevice(self.stages.focus_device_comboBox.currentText())

    def _on_xy_stage_position_changed(self, name, x, y):
        self.stages.x_lineEdit.setText(f"{x:.1f}")
        self.stages.y_lineEdit.setText(f"{y:.1f}")

    def _on_stage_position_changed(self, name, value):
        if "z" in name.lower():  # hack
            self.stages.z_lineEdit.setText(f"{value:.1f}")

    def stage_x_left(self):
        self._mmc.setRelativeXYPosition(
            -float(self.stages.xy_step_size_SpinBox.value()), 0.0
        )
        if self.stages.snap_on_click_checkBox.isChecked():
            self.snap()

    def stage_x_right(self):
        self._mmc.setRelativeXYPosition(
            float(self.stages.xy_step_size_SpinBox.value()), 0.0
        )
        if self.stages.snap_on_click_checkBox.isChecked():
            self.snap()

    def stage_y_up(self):
        self._mmc.setRelativeXYPosition(
            0.0,
            float(self.stages.xy_step_size_SpinBox.value()),
        )
        if self.stages.snap_on_click_checkBox.isChecked():
            self.snap()

    def stage_y_down(self):
        self._mmc.setRelativeXYPosition(
            0.0,
            -float(self.stages.xy_step_size_SpinBox.value()),
        )
        if self.stages.snap_on_click_checkBox.isChecked():
            self.snap()

    def stage_z_up(self):
        self._mmc.setRelativePosition(
            float(self.stages.z_step_size_doubleSpinBox.value())
        )
        if self.stages.snap_on_click_checkBox.isChecked():
            self.snap()

    def stage_z_down(self):
        self._mmc.setRelativePosition(
            -float(self.stages.z_step_size_doubleSpinBox.value())
        )
        if self.stages.snap_on_click_checkBox.isChecked():
            self.snap()

    # camera
    def _refresh_camera_options(self):
        cam_device = self._mmc.getCameraDevice()
        if not cam_device:
            return
        cam_props = self._mmc.getDevicePropertyNames(cam_device)
        if "Binning" in cam_props:
            bin_opts = self._mmc.getAllowedPropertyValues(cam_device, "Binning")
            with blockSignals(self.cam.bin_comboBox):
                self.cam.bin_comboBox.clear()
                self.cam.bin_comboBox.addItems(bin_opts)
                self.cam.bin_comboBox.setCurrentText(
                    self._mmc.getProperty(cam_device, "Binning")
                )

        if "PixelType" in cam_props:
            px_t = self._mmc.getAllowedPropertyValues(cam_device, "PixelType")
            with blockSignals(self.cam.bit_comboBox):
                self.cam.bit_comboBox.clear()
                self.cam.bit_comboBox.addItems(px_t)
                self.cam.bit_comboBox.setCurrentText(
                    self._mmc.getProperty(cam_device, "PixelType")
                )

    def bit_changed(self):
        if self.cam.bit_comboBox.count() > 0:
            bits = self.cam.bit_comboBox.currentText()
            self._mmc.setProperty(self._mmc.getCameraDevice(), "PixelType", bits)

    def bin_changed(self):
        if self.cam.bin_comboBox.count() > 0:
            bins = self.cam.bin_comboBox.currentText()
            cd = self._mmc.getCameraDevice()
            self._mmc.setProperty(cd, "Binning", bins)
