from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import napari
import numpy as np
from napari.experimental import link_layers
from pymmcore_plus import DeviceType
from pymmcore_plus._util import find_micromanager
from qtpy import QtWidgets as QtW
from qtpy.QtCore import QTimer
from qtpy.QtGui import QColor, QIcon
from superqt.utils import create_worker, ensure_main_thread, signals_blocked

from . import _core, _mda
from ._camera_roi import CameraROI
from ._core_widgets import PropertyBrowser
from ._gui_objects._mm_widget import MicroManagerWidget
from ._saving import save_sequence
from ._util import SelectDeviceFromCombobox, event_indices, extend_array_for_index

if TYPE_CHECKING:
    import napari.layers
    import napari.viewer
    import useq
    from pymmcore_plus.core.events import QCoreSignaler
    from pymmcore_plus.mda import PMDAEngine

ICONS = Path(__file__).parent / "icons"
CAM_ICON = QIcon(str(ICONS / "vcam.svg"))
CAM_STOP_ICON = QIcon(str(ICONS / "cam_stop.svg"))


class MainWindow(MicroManagerWidget):
    def __init__(self, viewer: napari.viewer.Viewer, remote=False):
        super().__init__()

        # create connection to mmcore server or process-local variant
        self._mmc = _core.get_core_singleton(remote)

        self.viewer = viewer

        adapter_path = find_micromanager()
        if not adapter_path:
            raise RuntimeError(
                "Could not find micromanager adapters. Please run "
                "`python -m pymmcore_plus.install` or install manually and set "
                "MICROMANAGER_PATH."
            )

        # add mda and explorer tabs to mm_tab widget
        sizepolicy = QtW.QSizePolicy(
            QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Expanding
        )
        self.tab_wdg.setSizePolicy(sizepolicy)

        self.streaming_timer: QTimer | None = None

        # disable gui
        self._set_enabled(False)

        # connect mmcore signals
        sig: QCoreSignaler = self._mmc.events

        # note: don't use lambdas with closures on `self`, since the connection
        # to core may outlive the lifetime of this particular widget.
        sig.systemConfigurationLoaded.connect(self._on_system_cfg_loaded)
        sig.XYStagePositionChanged.connect(self._on_xy_stage_position_changed)
        sig.stagePositionChanged.connect(self._on_stage_position_changed)
        sig.exposureChanged.connect(self._update_live_exp)

        # mda events
        self._mmc.mda.events.frameReady.connect(self._on_mda_frame)
        self._mmc.mda.events.sequenceStarted.connect(self._on_mda_started)
        self._mmc.mda.events.sequenceFinished.connect(self._on_mda_finished)
        self._mmc.events.mdaEngineRegistered.connect(self._update_mda_engine)

        self._mmc.events.startContinuousSequenceAcquisition.connect(self._start_live)
        self._mmc.events.stopSequenceAcquisition.connect(self._stop_live)

        # connect buttons
        self.stage_wdg.left_Button.clicked.connect(self.stage_x_left)
        self.stage_wdg.right_Button.clicked.connect(self.stage_x_right)
        self.stage_wdg.y_up_Button.clicked.connect(self.stage_y_up)
        self.stage_wdg.y_down_Button.clicked.connect(self.stage_y_down)
        self.stage_wdg.up_Button.clicked.connect(self.stage_z_up)
        self.stage_wdg.down_Button.clicked.connect(self.stage_z_down)
        self.tab_wdg.snap_Button.clicked.connect(self.snap)

        # connect comboBox
        self.stage_wdg.focus_device_comboBox.currentTextChanged.connect(
            self._set_focus_device
        )

        self.tab_wdg.snap_channel_comboBox.currentTextChanged.connect(
            self._channel_changed
        )

        self.cam_roi = CameraROI(
            self.viewer,
            self._mmc,
            self.cam_wdg.cam_roi_combo,
            self.cam_wdg.crop_btn,
        )

        # refresh options in case a config is already loaded by another remote
        if remote:
            self._refresh_options()

        self.viewer.layers.events.connect(self.update_max_min)
        self.viewer.layers.selection.events.active.connect(self.update_max_min)
        self.viewer.dims.events.current_step.connect(self.update_max_min)
        self.viewer.mouse_drag_callbacks.append(self._get_event_explorer)

        self._add_menu()

    def _add_menu(self):
        w = getattr(self.viewer, "__wrapped__", self.viewer).window  # don't do this.
        self._menu = QtW.QMenu("&Micro-Manager", w._qt_window)

        action = self._menu.addAction("Device Property Browser...")
        action.triggered.connect(self._show_prop_browser)

        bar = w._qt_window.menuBar()
        bar.insertMenu(list(bar.actions())[-1], self._menu)

    def _show_prop_browser(self):
        if not hasattr(self, "_prop_browser"):
            self._prop_browser = PropertyBrowser(self._mmc, self)
        self._prop_browser.show()
        self._prop_browser.raise_()

    def _on_system_cfg_loaded(self):
        if len(self._mmc.getLoadedDevices()) > 1:
            self._set_enabled(True)
            self._refresh_options()

    def _set_enabled(self, enabled):
        if self._mmc.getCameraDevice():
            self._camera_group_wdg(enabled)
            self.tab_wdg.snap_live_tab.setEnabled(enabled)
            self.tab_wdg.snap_live_tab.setEnabled(enabled)
        else:
            self._camera_group_wdg(False)
            self.tab_wdg.snap_live_tab.setEnabled(False)
            self.tab_wdg.snap_live_tab.setEnabled(False)

        if self._mmc.getXYStageDevice():
            self.stage_wdg.XY_groupBox.setEnabled(enabled)
        else:
            self.stage_wdg.XY_groupBox.setEnabled(False)

        if self._mmc.getFocusDevice():
            self.stage_wdg.Z_groupBox.setEnabled(enabled)
        else:
            self.stage_wdg.Z_groupBox.setEnabled(False)

        self.illum_btn.setEnabled(enabled)

        self.mda._set_enabled(enabled)
        if self._mmc.getXYStageDevice():
            self.explorer._set_enabled(enabled)
        else:
            self.explorer._set_enabled(False)

    def _camera_group_wdg(self, enabled):
        self.cam_wdg.setEnabled(enabled)

    def _refresh_options(self):
        self._refresh_channel_list()
        self._refresh_positions()
        self._refresh_xyz_devices()

    @ensure_main_thread
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

        if self.tab_wdg.tabWidget.currentIndex() != 0:
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

        self.tab_wdg.max_min_val_label.setText(min_max_txt)

    def snap(self):
        if self._mmc.isSequenceRunning():
            self._mmc.stopSequenceAcquisition()
        # snap in a thread so we don't freeze UI when using process local mmc
        create_worker(
            self._mmc.snapImage,
            _connect={"finished": lambda: self.update_viewer(self._mmc.getImage())},
            _start_thread=True,
        )

    def _start_live(self):
        self.streaming_timer = QTimer()
        self.streaming_timer.timeout.connect(self.update_viewer)
        self.streaming_timer.start(self._mmc.getExposure())

    def _stop_live(self):
        if self.streaming_timer:
            self.streaming_timer.stop()
            self.streaming_timer = None

    def _update_mda_engine(self, newEngine: PMDAEngine, oldEngine: PMDAEngine):
        oldEngine.events.frameReady.connect(self._on_mda_frame)
        oldEngine.events.sequenceStarted.disconnect(self._on_mda_started)
        oldEngine.events.sequenceFinished.disconnect(self._on_mda_finished)

        newEngine.events.frameReady.connect(self._on_mda_frame)
        newEngine.events.sequenceStarted.connect(self._on_mda_started)
        newEngine.events.sequenceFinished.connect(self._on_mda_finished)

    def _on_mda_started(self, sequence: useq.MDASequence):
        """ "create temp folder and block gui when mda starts."""
        self._set_enabled(False)

        self._mda_meta = _mda.SEQUENCE_META.get(sequence, _mda.SequenceMeta())
        if self._mda_meta.mode == "":
            # originated from user script - assume it's an mda
            self._mda_meta.mode = "mda"

    @ensure_main_thread
    def _on_mda_frame(self, image: np.ndarray, event: useq.MDAEvent):

        meta = self._mda_meta
        if meta.mode == "mda":

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
                layer = self.viewer.add_image(
                    _image, name=layer_name, blending="additive"
                )

                # dimensions labels
                labels = [i for i in seq.axis_order if i in event.index] + ["y", "x"]
                self.viewer.dims.axis_labels = labels

                # add metadata to layer
                layer.metadata["useq_sequence"] = seq
                layer.metadata["uid"] = seq.uid
                # storing event.index in addition to channel.config because it's
                # possible to have two of the same channel in one sequence.
                layer.metadata[
                    "ch_id"
                ] = f'{event.channel.config}_idx{event.index["c"]}'
        elif meta.mode == "explorer":

            seq = event.sequence

            meta = _mda.SEQUENCE_META.get(seq) or _mda.SequenceMeta()
            if meta.mode != "explorer":
                return

            x = event.x_pos / self.explorer.pixel_size
            y = event.y_pos / self.explorer.pixel_size * (-1)

            pos_idx = event.index["p"]
            file_name = meta.file_name if meta.should_save else "Exp"
            ch_name = event.channel.config
            ch_id = event.index["c"]
            layer_name = f"Pos{pos_idx:03d}_{file_name}_{ch_name}_idx{ch_id}"

            meta = dict(
                useq_sequence=seq,
                uid=seq.uid,
                scan_coord=(y, x),
                scan_position=f"Pos{pos_idx:03d}",
                ch_name=ch_name,
                ch_id=ch_id,
            )
            self.viewer.add_image(
                image,
                name=layer_name,
                blending="additive",
                translate=(y, x),
                metadata=meta,
            )

            zoom_out_factor = (
                self.explorer.scan_size_r
                if self.explorer.scan_size_r >= self.explorer.scan_size_c
                else self.explorer.scan_size_c
            )
            self.viewer.camera.zoom = 1 / zoom_out_factor
            self.viewer.reset_view()

    def _on_mda_finished(self, sequence: useq.MDASequence):
        """Save layer and add increment to save name."""
        meta = _mda.SEQUENCE_META.get(sequence) or _mda.SequenceMeta()
        seq_uid = sequence.uid
        if meta.mode == "explorer":

            layergroups = defaultdict(set)
            for lay in self.viewer.layers:
                if lay.metadata.get("uid") == seq_uid:
                    key = f"{lay.metadata['ch_name']}_idx{lay.metadata['ch_id']}"
                    layergroups[key].add(lay)
            for group in layergroups.values():
                link_layers(group)
        meta = _mda.SEQUENCE_META.pop(sequence, self._mda_meta)
        save_sequence(sequence, self.viewer.layers, meta)
        # reactivate gui when mda finishes.
        self._set_enabled(True)

    def _get_event_explorer(self, viewer, event):
        if not self.explorer.isVisible():
            return
        if self._mmc.getPixelSizeUm() > 0:
            width = self._mmc.getROI(self._mmc.getCameraDevice())[2]
            height = self._mmc.getROI(self._mmc.getCameraDevice())[3]

            x = viewer.cursor.position[-1] * self._mmc.getPixelSizeUm()
            y = viewer.cursor.position[-2] * self._mmc.getPixelSizeUm() * (-1)

            # to match position coordinates with center of the image
            x = f"{x - ((width / 2) * self._mmc.getPixelSizeUm()):.1f}"
            y = f"{y - ((height / 2) * self._mmc.getPixelSizeUm() * (-1)):.1f}"

        else:
            x, y = "None", "None"

        self.explorer.x_lineEdit.setText(x)
        self.explorer.y_lineEdit.setText(y)

    def _update_live_exp(self, camera: str, exposure: float):
        if self.streaming_timer:
            self.streaming_timer.setInterval(int(exposure))
            self._mmc.stopSequenceAcquisition()
            self._mmc.startContinuousSequenceAcquisition(exposure)

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
        with signals_blocked(self.tab_wdg.snap_channel_comboBox):
            self.tab_wdg.snap_channel_comboBox.clear()
            self.tab_wdg.snap_channel_comboBox.addItems(channel_list)
            self.tab_wdg.snap_channel_comboBox.setCurrentText(
                self._mmc.getCurrentConfig(channel_group)
            )

    def _on_config_set(self, groupName: str, configName: str):
        if groupName == self._mmc.getOrGuessChannelGroup():
            with signals_blocked(self.tab_wdg.snap_channel_comboBox):
                self.tab_wdg.snap_channel_comboBox.setCurrentText(configName)

    def _channel_changed(self, newChannel: str):
        self._mmc.setConfig(self._mmc.getChannelGroup(), newChannel)

    # stages
    def _refresh_positions(self):
        if self._mmc.getXYStageDevice():
            x, y = self._mmc.getXPosition(), self._mmc.getYPosition()
            self._on_xy_stage_position_changed(self._mmc.getXYStageDevice(), x, y)
            self.stage_wdg.XY_groupBox.setEnabled(True)
        else:
            self.stage_wdg.XY_groupBox.setEnabled(False)

        if self._mmc.getFocusDevice():
            self.stage_wdg.z_lineEdit.setText(f"{self._mmc.getZPosition():.1f}")
            self.stage_wdg.Z_groupBox.setEnabled(True)
        else:
            self.stage_wdg.Z_groupBox.setEnabled(False)

    def _refresh_xyz_devices(self):

        # since there is no offset control yet:
        self.stage_wdg.offset_Z_groupBox.setEnabled(False)

        self.stage_wdg.focus_device_comboBox.clear()
        self.stage_wdg.xy_device_comboBox.clear()

        xy_stage_devs = list(self._mmc.getLoadedDevicesOfType(DeviceType.XYStageDevice))

        focus_devs = list(self._mmc.getLoadedDevicesOfType(DeviceType.StageDevice))

        if not xy_stage_devs:
            self.stage_wdg.XY_groupBox.setEnabled(False)
        else:
            self.stage_wdg.XY_groupBox.setEnabled(True)
            self.stage_wdg.xy_device_comboBox.addItems(xy_stage_devs)
            self._set_xy_stage_device()

        if not focus_devs:
            self.stage_wdg.Z_groupBox.setEnabled(False)
        else:
            self.stage_wdg.Z_groupBox.setEnabled(True)
            self.stage_wdg.focus_device_comboBox.addItems(focus_devs)
            self._set_focus_device()

    def _set_xy_stage_device(self):
        if not self.stage_wdg.xy_device_comboBox.count():
            return
        self._mmc.setXYStageDevice(self.stage_wdg.xy_device_comboBox.currentText())

    def _set_focus_device(self):
        if not self.stage_wdg.focus_device_comboBox.count():
            return
        self._mmc.setFocusDevice(self.stage_wdg.focus_device_comboBox.currentText())

    def _on_xy_stage_position_changed(self, name, x, y):
        self.stage_wdg.x_lineEdit.setText(f"{x:.1f}")
        self.stage_wdg.y_lineEdit.setText(f"{y:.1f}")

    def _on_stage_position_changed(self, name, value):
        if "z" in name.lower():  # hack
            self.stage_wdg.z_lineEdit.setText(f"{value:.1f}")

    def stage_x_left(self):
        self._mmc.setRelativeXYPosition(
            -float(self.stage_wdg.xy_step_size_SpinBox.value()), 0.0
        )
        if self.stage_wdg.snap_on_click_checkBox.isChecked():
            self.snap()

    def stage_x_right(self):
        self._mmc.setRelativeXYPosition(
            float(self.stage_wdg.xy_step_size_SpinBox.value()), 0.0
        )
        if self.stage_wdg.snap_on_click_checkBox.isChecked():
            self.snap()

    def stage_y_up(self):
        self._mmc.setRelativeXYPosition(
            0.0,
            float(self.stage_wdg.xy_step_size_SpinBox.value()),
        )
        if self.stage_wdg.snap_on_click_checkBox.isChecked():
            self.snap()

    def stage_y_down(self):
        self._mmc.setRelativeXYPosition(
            0.0,
            -float(self.stage_wdg.xy_step_size_SpinBox.value()),
        )
        if self.stage_wdg.snap_on_click_checkBox.isChecked():
            self.snap()

    def stage_z_up(self):
        self._mmc.setRelativePosition(
            float(self.stage_wdg.z_step_size_doubleSpinBox.value())
        )
        if self.stage_wdg.snap_on_click_checkBox.isChecked():
            self.snap()

    def stage_z_down(self):
        self._mmc.setRelativePosition(
            -float(self.stage_wdg.z_step_size_doubleSpinBox.value())
        )
        if self.stage_wdg.snap_on_click_checkBox.isChecked():
            self.snap()
