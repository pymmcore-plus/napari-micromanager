from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from pymmcore_plus import CMMCorePlus, RemoteMMCore
from qtpy import QtWidgets as QtW
from qtpy import uic
from qtpy.QtCore import QSize, QTimer
from qtpy.QtGui import QIcon

from ._util import extend_array_for_index
from .explore_sample import ExploreSample
from .multid_widget import MultiDWidget

if TYPE_CHECKING:
    import napari.layers
    import napari.viewer
    import useq


ICONS = Path(__file__).parent / "icons"
CAM_ICON = QIcon(str(ICONS / "vcam.svg"))
CAM_STOP_ICON = QIcon(str(ICONS / "cam_stop.svg"))


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
    Z_groupBox: QtW.QGroupBox
    left_Button: QtW.QPushButton
    right_Button: QtW.QPushButton
    y_up_Button: QtW.QPushButton
    y_down_Button: QtW.QPushButton
    up_Button: QtW.QPushButton
    down_Button: QtW.QPushButton
    xy_step_size_SpinBox: QtW.QSpinBox
    z_step_size_doubleSpinBox: QtW.QDoubleSpinBox
    tabWidget: QtW.QTabWidget
    snap_live_tab: QtW.QWidget
    multid_tab: QtW.QWidget
    snap_channel_groupBox: QtW.QGroupBox
    snap_channel_comboBox: QtW.QComboBox
    exp_spinBox: QtW.QDoubleSpinBox
    snap_Button: QtW.QPushButton
    live_Button: QtW.QPushButton
    max_val_lineEdit: QtW.QLineEdit
    min_val_lineEdit: QtW.QLineEdit
    px_size_doubleSpinBox: QtW.QDoubleSpinBox

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

        # create connection to mmcore server or process-local variant
        self._mmc = RemoteMMCore() if remote else CMMCorePlus()

        # tab widgets
        self.mda = MultiDWidget(self._mmc)
        self.explorer = ExploreSample(self._mmc)
        self.tabWidget.addTab(self.mda, "Multi-D Acquisition")
        self.tabWidget.addTab(self.explorer, "Sample Explorer")

        # # connect mmcore signals
        sig = self._mmc.events

        # note: don't use lambdas with closures on `self`, since the connection
        # to core may outlive the lifetime of this particular widget.
        sig.sequenceFinished.connect(self._on_system_configuration_loaded)
        sig.systemConfigurationLoaded.connect(self._on_system_configuration_loaded)
        sig.XYStagePositionChanged.connect(self._on_xy_stage_position_changed)
        sig.stagePositionChanged.connect(self._on_stage_position_changed)
        sig.exposureChanged.connect(self._on_exp_change)
        sig.frameReady.connect(self._on_mda_frame)
        sig.channelGroupChanged.connect(self._refresh_channel_list)
        sig.configSet.connect(self._on_config_set)

        # connect explorer
        self.explorer.new_frame.connect(self.add_frame_explorer)
        self.explorer.delete_snaps.connect(self.delete_layer)
        self.explorer.delete_previous_scan.connect(self.delete_layer)

        # connect buttons
        self.load_cfg_Button.clicked.connect(self.load_cfg)
        self.browse_cfg_Button.clicked.connect(self.browse_cfg)
        self.left_Button.clicked.connect(self.stage_x_left)
        self.right_Button.clicked.connect(self.stage_x_right)
        self.y_up_Button.clicked.connect(self.stage_y_up)
        self.y_down_Button.clicked.connect(self.stage_y_down)
        self.up_Button.clicked.connect(self.stage_z_up)
        self.down_Button.clicked.connect(self.stage_z_down)
        self.snap_Button.clicked.connect(self.snap)
        self.live_Button.clicked.connect(self.toggle_live)

        # connect comboBox
        self.objective_comboBox.currentIndexChanged.connect(self.change_objective)
        self.bit_comboBox.currentIndexChanged.connect(self.bit_changed)
        self.bin_comboBox.currentIndexChanged.connect(self.bin_changed)
        self.snap_channel_comboBox.currentTextChanged.connect(self._channel_changed)

    def _on_config_set(self, groupName: str, configName: str):
        if groupName == self._get_channel_group():
            self.snap_channel_comboBox.blockSignals(True)
            self.snap_channel_comboBox.setCurrentText(configName)
            self.snap_channel_comboBox.blockSignals(False)

    def _on_exp_change(self, camera: str, exposure: float):
        self.exp_spinBox.setValue(exposure)

    def delete_layer(self, name):
        layer_set = {str(layer) for layer in self.viewer.layers}
        if name in layer_set:
            self.viewer.layers.remove(name)
        layer_set.clear()

    def add_frame_explorer(self, name, array):
        layer_name = name
        try:
            layer = self.viewer.layers[layer_name]
            layer.data = array
        except KeyError:
            self.viewer.add_image(array, name=layer_name)

    # TO DO: add the file name form the save box
    def _on_mda_frame(self, image: np.ndarray, event: useq.MDAEvent):
        seq = event.sequence
        try:
            # see if we already have a layer with this sequence
            layer: napari.layers.Image = next(
                x for x in self.viewer.layers if x.metadata.get("uid") == seq.uid
            )

            # get the index of the incoming image
            im_idx = tuple(event.index[k] for k in seq.axis_order if k in event.index)
            # make sure array shape contains im_idx, or pad with zeros
            new_array = extend_array_for_index(layer.data, im_idx)
            # add the incoming index at the appropriate index
            new_array[im_idx] = image

            # set layer data
            layer.data = new_array

            for a, v in enumerate(im_idx):
                self.viewer.dims.set_point(a, v)

        except StopIteration:
            layer_name = f"mda_{datetime.now().strftime('%H:%M:%S')}"
            _image = image[(np.newaxis,) * len(seq.shape)]
            layer = self.viewer.add_image(_image, name=layer_name)
            labels = [i for i in seq.axis_order if i in event.index] + ["y", "x"]

            self.viewer.dims.axis_labels = labels
            layer.metadata["useq_sequence"] = seq
            layer.metadata["uid"] = seq.uid

            layer = self.viewer.layers[layer_name]

    def browse_cfg(self):
        self._mmc.unloadAllDevices()  # unload all devicies
        print(f"Loaded Devices: {self._mmc.getLoadedDevices()}")

        # clear spinbox/combobox
        self.objective_comboBox.clear()
        self.bin_comboBox.clear()
        self.bit_comboBox.clear()
        self.snap_channel_comboBox.clear()

        file_dir = QtW.QFileDialog.getOpenFileName(self, "", "⁩", "cfg(*.cfg)")
        self.cfg_LineEdit.setText(str(file_dir[0]))
        # self.setEnabled(False)
        self.max_val_lineEdit.setText("None")
        self.min_val_lineEdit.setText("None")
        self.load_cfg_Button.setEnabled(True)

    def load_cfg(self):
        self.load_cfg_Button.setEnabled(False)
        print("loading", self.cfg_LineEdit.text())
        self._mmc.loadSystemConfiguration(self.cfg_LineEdit.text())

    def _refresh_camera_options(self):
        cam_device = self._mmc.getCameraDevice()
        cam_props = self._mmc.getDevicePropertyNames(cam_device)
        if "Binning" in cam_props:
            bin_opts = self._mmc.getAllowedPropertyValues(cam_device, "Binning")
            self.bin_comboBox.addItems(bin_opts)
            self.bin_comboBox.setCurrentText(
                self._mmc.getProperty(cam_device, "Binning")
            )

        if "PixelType" in cam_props:
            px_t = self._mmc.getAllowedPropertyValues(cam_device, "PixelType")
            self.bit_comboBox.addItems(px_t)
            if "16" in px_t:
                self.bit_comboBox.setCurrentText("16bit")
                self._mmc.setProperty(cam_device, "PixelType", "16bit")

    def _refresh_objective_options(self):
        if "Objective" in self._mmc.getLoadedDevices():
            self.objective_comboBox.addItems(self._mmc.getStateLabels("Objective"))

    def _refresh_channel_list(self, channel_group: str = None):
        if channel_group is None:
            channel_group = self._get_channel_group()
        if channel_group:
            channel_list = list(self._mmc.getAvailableConfigs(channel_group))
            self.snap_channel_comboBox.addItems(channel_list)
            self.explorer.scan_channel_comboBox.addItems(channel_list)

    def _on_system_configuration_loaded(self):
        self._refresh_camera_options()
        self._refresh_objective_options()
        self._refresh_channel_list()
        if self._mmc.getXYStageDevice():
            x, y = self._mmc.getXPosition(), self._mmc.getYPosition()
            self._on_xy_stage_position_changed(self._mmc.getXYStageDevice(), x, y)

    def bit_changed(self):
        if self.bit_comboBox.count() > 0:
            bits = self.bit_comboBox.currentText()
            self._mmc.setProperty(self._mmc.getCameraDevice(), "PixelType", bits)

    def bin_changed(self):
        if self.bin_comboBox.count() > 0:
            bins = self.bin_comboBox.currentText()
            cd = self._mmc.getCameraDevice()
            self._mmc.setProperty(cd, "Binning", bins)

    def _get_channel_group(self) -> str | None:
        """
        Get channelGroup falling back to Channel if not set, also
        check that this is an availableConfigGroup.
        """
        chan_group = self._mmc.getChannelGroup()
        if chan_group == "":
            # not set in core. Try "Channel" as a fallback
            chan_group = "Channel"
        if chan_group in self._mmc.getAvailableConfigGroups():
            return chan_group

    def _channel_changed(self, newChannel: str):
        self._mmc.setConfig(self._get_channel_group(), newChannel)

    def _on_xy_stage_position_changed(self, name, x, y):
        self.x_lineEdit.setText(f"{x:.1f}")
        self.y_lineEdit.setText(f"{y:.1f}")

    def _on_stage_position_changed(self, name, value):
        if "z" in name.lower():  # hack
            self.z_lineEdit.setText(f"{value:.1f}")

    def stage_x_left(self):
        self._mmc.setRelPosition(dx=-float(self.xy_step_size_SpinBox.value()))

    def stage_x_right(self):
        self._mmc.setRelPosition(dx=float(self.xy_step_size_SpinBox.value()))

    def stage_y_up(self):
        self._mmc.setRelPosition(dy=float(self.xy_step_size_SpinBox.value()))

    def stage_y_down(self):
        self._mmc.setRelPosition(dy=-float(self.xy_step_size_SpinBox.value()))

    def stage_z_up(self):
        self._mmc.setRelPosition(dz=float(self.z_step_size_doubleSpinBox.value()))

    def stage_z_down(self):
        self._mmc.setRelPosition(dz=-float(self.z_step_size_doubleSpinBox.value()))

    def change_objective(self):
        if self.objective_comboBox.count() <= 0:
            return

        zdev = self._mmc.getFocusDevice()

        currentZ = self._mmc.getZPosition()
        self._mmc.setPosition(zdev, 0)
        self._mmc.waitForDevice(zdev)
        self._mmc.setProperty(
            "Objective", "Label", self.objective_comboBox.currentText()
        )
        self._mmc.waitForDevice("Objective")
        self._mmc.setPosition(zdev, currentZ)
        self._mmc.waitForDevice(zdev)

        # define and set pixel size Config
        self._mmc.deletePixelSizeConfig(self._mmc.getCurrentPixelSizeConfig())
        curr_obj_name = self._mmc.getProperty("Objective", "Label")
        self._mmc.definePixelSizeConfig(curr_obj_name)
        self._mmc.setPixelSizeConfig(curr_obj_name)

        # get magnification info from the objective name
        # and set image pixel sixe (x,y) for the current pixel size Config
        match = re.search(r"(\d{1,3})[xX]", curr_obj_name)
        if match:
            mag = int(match.groups()[0])
            self.image_pixel_size = self.px_size_doubleSpinBox.value() / mag
            self._mmc.setPixelSizeUm(
                self._mmc.getCurrentPixelSizeConfig(), self.image_pixel_size
            )

    def update_viewer(self, data=None):
        if data is None:
            try:
                data = self._mmc.popNextImage()
            except (RuntimeError, IndexError):
                # circular buffer empty
                return
        try:
            self.viewer.layers["preview"].data = data
        except KeyError:
            self.viewer.add_image(data, name="preview")

    def snap(self):
        self.stop_live()
        self._mmc.setExposure(self.exp_spinBox.value())
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
            self.start_live()
            self.live_Button.setIcon(CAM_STOP_ICON)
        else:
            self.stop_live()
            self.live_Button.setIcon(CAM_ICON)
