from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import napari
import numpy as np
from loguru import logger
from magicgui.widgets import ComboBox, FloatSlider, LineEdit, Slider
from pymmcore_plus import CMMCorePlus, RemoteMMCore
from qtpy import QtWidgets as QtW
from qtpy import uic
from qtpy.QtCore import QSize, Qt, QTimer, Signal
from qtpy.QtGui import QColor, QIcon

from ._camera_roi import CameraROI
from ._group_and_presets_tab import GroupPresetWidget, RenameGroupPreset
from ._illumination import IlluminationDialog
from ._properties_table_with_checkbox import GroupConfigurations
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
WDG_TYPE = (FloatSlider, Slider, LineEdit)


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
    max_min_val_label: QtW.QLabel
    px_size_doubleSpinBox: QtW.QDoubleSpinBox
    properties_Button: QtW.QPushButton
    cam_roi_comboBox: QtW.QComboBox
    crop_Button: QtW.QPushButton
    illumination_Button: QtW.QPushButton
    snap_on_click_xy_checkBox: QtW.QCheckBox
    snap_on_click_z_checkBox: QtW.QCheckBox

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

    update_cbox_widget = Signal(str, str)

    def __init__(self, viewer: napari.viewer.Viewer, remote=True):
        super().__init__()
        self.setup_ui()

        self.viewer = viewer
        self.streaming_timer = None

        self.objectives_device = None
        self.objectives_cfg = None

        self.dict_group_presets_table = {
            "groups": [],
            "presets": [],
            "current_preset": [],
            "device": [],
            "property": [],
        }

        # create connection to mmcore server or process-local variant
        self._mmc = RemoteMMCore(verbose=False) if remote else CMMCorePlus()

        self.cfg_LineEdit.setText(
            str(Path(__file__).parent.parent / "tests" / "test_config.cfg")
        )

        # tab widgets
        # create groups and presets tab
        self.groups_and_presets = GroupPresetWidget(self._mmc)
        self.tabWidget.addTab(self.groups_and_presets, "Groups and Presets")
        self.tabWidget.tabBar().moveTab(1, 0)
        self.table = self.groups_and_presets.tb
        # connect signals from groups and presets tab
        self.groups_and_presets.table_wdg_changed.connect(self._change_channel_main_gui)
        self.groups_and_presets.table_wdg_changed.connect(
            self._change_objective_main_gui
        )

        # create mda and exporer tab
        self.mda = MultiDWidget(self._mmc)
        self.explorer = ExploreSample(self.viewer, self._mmc)
        self.tabWidget.addTab(self.mda, "Multi-D Acquisition")
        self.tabWidget.addTab(self.explorer, "Sample Explorer")

        self.tabWidget.setMovable(True)
        self.tabWidget.setCurrentIndex(0)

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

        self.illumination_Button.clicked.connect(self.illumination)
        self.properties_Button.clicked.connect(self._show_prop_browser)

        # connect GroupPresetWidget
        self.groups_and_presets.new_btn.clicked.connect(
            self._create_group_presets
        )  # + group/preset
        self.groups_and_presets.edit_btn.clicked.connect(
            self._edit_group_presets
        )  # edit group/preset
        self.groups_and_presets.rename_btn.clicked.connect(
            self._open_rename_widget
        )  # rename group/preset
        self.groups_and_presets.save_cfg_btn.clicked.connect(
            self._save_cfg
        )  # save group/preset .cfg

        # connect comboBox
        self.objective_comboBox.currentTextChanged.connect(
            self._change_objective_main_gui
        )
        self.bit_comboBox.currentIndexChanged.connect(self.bit_changed)
        self.bin_comboBox.currentIndexChanged.connect(self.bin_changed)
        self.snap_channel_comboBox.currentTextChanged.connect(
            self._change_channel_main_gui
        )

        self.cam_roi = CameraROI(
            self.viewer, self._mmc, self.cam_roi_comboBox, self.crop_Button
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
            px_cfg = self._mmc.getCurrentPixelSizeConfig()
            logger.debug(f"pixel config:{px_cfg} -> pixel size: {value}")

        @sig.configSet.connect
        def _on_config_set(groupName: str, configName: str):
            logger.debug(f"CFG SET: {groupName} -> {configName}")

            if groupName == self.objectives_cfg:
                self._update_pixel_size()

        @sig.propertyChanged.connect
        def _on_prop_changed(dev, prop, val):
            # logger.debug(f"PROP CHANGED: {dev}.{prop} -> {val}")

            # Camera gui options -> change gui widgets
            if dev == self._mmc.getCameraDevice():
                self._refresh_camera_options()

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

    def illumination(self):
        if not hasattr(self, "_illumination"):
            self._illumination = IlluminationDialog(self._mmc, self)
        self._illumination.show()

    def _show_prop_browser(self):
        pb = PropBrowser(self._mmc, self)
        pb.exec()

    def _create_group_presets(self):
        if hasattr(self, "edit_gp_ps_widget"):
            self.edit_gp_ps_widget.close()
        if not hasattr(self, "create_gp_ps_widget"):
            self.create_gp_ps_widget = GroupConfigurations(self._mmc, self)
            self.create_gp_ps_widget.new_group_preset.connect(
                self._update_group_preset_table
            )
        self.create_gp_ps_widget._reset_comboboxes()
        self.create_gp_ps_widget.show()

    def _get_dict_group_presets_table_data(self, dict: dict):
        dict["groups"] = []
        dict["presets"] = []
        dict["current_preset"] = []
        dict["device"] = []
        dict["property"] = []

        for row in range(self.table.shape[0]):
            group, wdg = self.table.data[row]

            if isinstance(wdg, WDG_TYPE):
                dict["groups"].append("")
                dict["presets"].append("")
                dict["current_preset"].append("")
                dict["device"].append(wdg.annotation[0])
                dict["property"].append(wdg.annotation[1])
            else:
                cbox_items = [wdg.native.itemText(i) for i in range(wdg.native.count())]
                dict["groups"].append(group)
                dict["presets"].append(cbox_items)
                dict["current_preset"].append(wdg.get_value())
                dict["device"].append("")
                dict["property"].append("")

    def _update_group_preset_table(self, group: str, preset: str):
        logger.debug(f"signal recived: {group}, {preset}")

        groups_list = list(self._mmc.getAvailableConfigGroups())
        groups_diff = list(
            set(groups_list) ^ set(self.dict_group_presets_table["groups"])
        )

        if group in groups_diff:
            rowPosition = self.table.native.rowCount()
            self.table.native.insertRow(rowPosition)
            self.table.native.setItem(rowPosition, 0, QtW.Qself.tableWidgetItem(group))
            wdg = self.groups_and_presets._set_widget(group, [preset])
            self.table.native.setCellWidget(rowPosition, 1, wdg.native)
            logger.debug(f"{group} group added")

        else:
            # row  =

            for row in range(self.table.shape[0]):
                gp, wdg = self.table.data[row]
                if isinstance(wdg, ComboBox) and group == gp:
                    wdg_items = list(wdg.choices)
                    prs = list(self._mmc.getAvailableConfigs(group))
                    preset_diff = list(set(wdg_items) ^ set(prs))
                    for p in preset_diff:
                        wdg_items.append(str(p))
                        logger.debug(f"{p} preset added to {group} group")
                        wdg.choices = wdg_items

        self._get_dict_group_presets_table_data(self.dict_group_presets_table)
        self._update_objectives_combobox()
        self._update_channels_combobox()

    def _update_objectives_combobox(self):
        # populate objective combobox when creating/modifying objective group
        if self.objectives_cfg:
            obj_gp_list = [
                self.objective_comboBox.itemText(i)
                for i in range(self.objective_comboBox.count())
            ]
            obj_cfg_list = list(self._mmc.getAvailableConfigs(self.objectives_cfg))
            obj_gp_list.sort()
            obj_cfg_list.sort()

            if obj_gp_list != obj_cfg_list:
                self._refresh_objective_options()

    def _update_channels_combobox(self):
        # populate gui channel combobox when creating/modifying the channel group
        if not self._mmc.getChannelGroup():
            self._refresh_channel_list()
        else:
            channel_list = list(
                self._mmc.getAvailableConfigs(self._mmc.getChannelGroup())
            )
            cbox_list = [
                self.snap_channel_comboBox.itemText(i)
                for i in range(self.snap_channel_comboBox.count())
            ]
            channel_list.sort()
            cbox_list.sort()
            if channel_list != cbox_list:
                self._refresh_channel_list()

    def _edit_group_presets(self):
        if hasattr(self, "create_gp_ps_widget"):
            self.create_gp_ps_widget.close()
        if not hasattr(self, "edit_gp_ps_widget"):
            self.edit_gp_ps_widget = GroupConfigurations(self._mmc, self)
            self.edit_gp_ps_widget.group_le.native.setReadOnly(True)
            self.edit_gp_ps_widget.preset_le.native.setReadOnly(True)
            self.edit_gp_ps_widget.new_group_preset.connect(
                self._update_group_preset_table_edit
            )
        self.edit_gp_ps_widget._reset_comboboxes()
        try:
            (
                group,
                preset,
                _to_find,
            ) = self.groups_and_presets._edit_selected_group_preset()
            self.edit_gp_ps_widget._set_checkboxes_status(group, preset, _to_find)
            self.edit_gp_ps_widget.show()

        except TypeError:
            pass

    def _update_group_preset_table_edit(self, group: str, preset: str):
        logger.debug(f"signal recived: {group}, {preset}")

        dev_prop_val_new = [
            (f"{key[0]}.{key[1]}", key[2])
            for key in self._mmc.getConfigData(group, preset)
        ]
        dev_prop_new = [x[0] for x in dev_prop_val_new]

        presets = self._mmc.getAvailableConfigs(group)
        for p in presets:

            if p == preset:
                continue

            dev_prop_old = [
                f"{key[0]}.{key[1]}" for key in self._mmc.getConfigData(group, p)
            ]

            diff = list(set(dev_prop_new) ^ set(dev_prop_old))

            for d in diff:
                if d not in dev_prop_old:
                    self._update_preset(
                        group,
                        preset,
                        dev_prop_val_new,
                        dev_prop_new,
                        p,
                        dev_prop_old,
                        d,
                    )
                else:
                    for prs in presets:
                        if prs == preset:
                            continue
                        self._mmc.deleteConfig(group, prs)

                        for tup in dev_prop_val_new:
                            dev = tup[0].split(".")[0]
                            prop = tup[0].split(".")[1]
                            val = tup[1]
                            self._mmc.defineConfig(group, prs, dev, prop, val)

                    self._create_and_add_widget(group, preset)
                    self._get_dict_group_presets_table_data(
                        self.dict_group_presets_table
                    )
                    self.edit_gp_ps_widget.close()
                    return

        self._get_dict_group_presets_table_data(self.dict_group_presets_table)

        self.edit_gp_ps_widget.close()

    def _update_preset(
        self, group, preset, dev_prop_val_new, dev_prop_new, p, dev_prop_old, d
    ):
        if [x for x in dev_prop_old if x in dev_prop_new]:
            dev = d.split(".")[0]
            prop = d.split(".")[1]
            val = [item[1] for item in dev_prop_val_new if item[0] == d][0]
            self._mmc.defineConfig(group, p, dev, prop, val)
        else:
            self._delete_preset_and_recreate(group, preset, dev_prop_val_new, p, d)

    def _delete_preset_and_recreate(self, group, preset, dev_prop_val_new, p, d):
        self._mmc.deleteConfig(group, p)
        for i in dev_prop_val_new:
            dev = i[0].split(".")[0]
            prop = i[0].split(".")[1]
            val = [item[1] for item in dev_prop_val_new if item[0] == d][0]
            self._mmc.defineConfig(group, p, dev, prop, val)
        self._create_and_add_widget(group, preset)

    def _create_and_add_widget(self, group, preset):
        wdg_items = self._mmc.getAvailableConfigs(group)
        new_wdg = self.groups_and_presets._set_widget(group, wdg_items)
        matching_items = self.table.native.findItems(group, Qt.MatchContains)
        row = matching_items[0].row()
        with blockSignals(new_wdg.native):
            self.table.native.removeCellWidget(row, 1)
            self.table.native.setCellWidget(row, 1, new_wdg.native)
            new_wdg.value = preset

    def _open_rename_widget(self):
        self._rw = RenameGroupPreset(self)
        self._rw.button.clicked.connect(self._rename_group_preset)
        # populate the rename widget with the group/preset to rename
        self.old_g, self.old_p = self._populate_rename_widget(self.table)
        self._rw.show()

    def _populate_rename_widget(self, table):
        selected_row = [r.row() for r in table.native.selectedIndexes()]
        print(selected_row)

        if not selected_row or len(selected_row) > 1:
            warnings.warn("Select one row!")
            return

        groupname = table.data[selected_row[0]][0]
        wdg = table.data[selected_row[0]][1]

        if isinstance(wdg, ComboBox):
            curr_preset = wdg.value
        else:
            curr_preset = wdg.name.translate({ord(c): None for c in "[]'"})

        self._rw.gp_lineedit.value = groupname
        self._rw.ps_lineedit.value = curr_preset

        return groupname, curr_preset

    def _rename_group_preset(self):

        channel_group = self._mmc.getChannelGroup()

        new_g = self._rw.gp_lineedit.value
        new_p = self._rw.ps_lineedit.value

        self._rw.close()

        self._mmc.renameConfigGroup(self.old_g, new_g)
        self._mmc.renameConfig(new_g, self.old_p, new_p)

        for row in range(self.table.shape[0]):
            gp, _ = self.table.data[row]

            if gp == self.old_g:

                self.table.native.removeCellWidget(row, 0)
                self.table.native.setItem(row, 0, QtW.QTableWidgetItem(new_g))

                wdg_items = self._mmc.getAvailableConfigs(new_g)

                new_wdg = self.groups_and_presets._set_widget(new_g, wdg_items)

                with blockSignals(new_wdg.native):
                    self.table.native.removeCellWidget(row, 1)
                    self.table.native.setCellWidget(row, 1, new_wdg.native)
                    new_wdg.value = new_p

                # update current channel group if == gp
                if gp == channel_group:  # cannot use mmc.getChannelGroup since empty
                    self._set_channel_group(new_g)
                # update current objective group if == gp
                if gp == self.objectives_cfg:
                    self.objectives_cfg = new_g
                    self._add_objective_to_gui(new_p, wdg_items)

        logger.debug(f"{self.old_g}-{self.old_p} renamed in {new_g}-{new_p}")

        self._get_dict_group_presets_table_data(self.dict_group_presets_table)

    def _save_cfg(self):
        current_cfg_path = Path(self.cfg_LineEdit.text())
        f_name = current_cfg_path.stem
        parent_path = current_cfg_path.parent
        print(current_cfg_path)
        print(parent_path)
        path_and_filename, _ = QtW.QFileDialog.getSaveFileName(
            self, "Save cfg File", f"{parent_path} / {f_name}", "cfg File (*cfg)"
        )
        self._mmc.saveSystemConfiguration(f"{path_and_filename}")

    def _set_enabled(self, enabled):
        self.objective_groupBox.setEnabled(enabled)
        self.illumination_Button.setEnabled(enabled)
        self.camera_groupBox.setEnabled(enabled)
        self.XY_groupBox.setEnabled(enabled)
        self.Z_groupBox.setEnabled(enabled)
        self.snap_live_tab.setEnabled(enabled)
        self.snap_live_tab.setEnabled(enabled)
        self.crop_Button.setEnabled(enabled)
        self.tabWidget.setEnabled(enabled)

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

        # clear spinbox/combobox without accidently setting properties
        boxes = [
            self.objective_comboBox,
            self.bin_comboBox,
            self.bit_comboBox,
            self.snap_channel_comboBox,
        ]
        with blockSignals(boxes):
            for box in boxes:
                box.clear()

        self.objectives_device = None
        self.objectives_cfg = None

        file_dir = QtW.QFileDialog.getOpenFileName(self, "", "", "cfg(*.cfg)")
        self.cfg_LineEdit.setText(str(file_dir[0]))
        self.max_min_val_label.setText("None")
        self.load_cfg_Button.setEnabled(True)

    def load_cfg(self):
        # disable gui
        self._set_enabled(False)
        self.load_cfg_Button.setEnabled(False)
        self._mmc.loadSystemConfiguration(self.cfg_LineEdit.text())
        logger.debug(f"Loaded Devices: {self._mmc.getLoadedDevices()}")
        self.groups_and_presets.populate_table()
        self._get_dict_group_presets_table_data(self.dict_group_presets_table)

        # enable gui
        self._set_enabled(True)

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
            self.objective_comboBox.clear()
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
        with blockSignals(self.objective_comboBox):
            self.objective_comboBox.clear()
            self.objective_comboBox.addItems(presets)
            if isinstance(current_obj, int):
                self.objective_comboBox.setCurrentIndex(current_obj)
            else:
                self.objective_comboBox.setCurrentText(current_obj)
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
            self.snap_channel_comboBox.clear()
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
        channel_list = list(self._mmc.getAvailableConfigs(channel_group))
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

    def _refresh_options(self):
        self._refresh_camera_options()
        self._refresh_objective_options()
        self._refresh_channel_list()
        self._refresh_positions()

        self.groups_and_presets.populate_table()

    def bit_changed(self):
        if self.bit_comboBox.count() > 0:
            bits = self.bit_comboBox.currentText()
            self._mmc.setProperty(self._mmc.getCameraDevice(), "PixelType", bits)

    def bin_changed(self):
        if self.bin_comboBox.count() > 0:
            bins = self.bin_comboBox.currentText()
            cd = self._mmc.getCameraDevice()
            self._mmc.setProperty(cd, "Binning", bins)

    def _change_channel_main_gui(self, newChannel: str):
        if self._mmc.getChannelGroup() and newChannel in list(
            self._mmc.getAvailableConfigs(self._mmc.getChannelGroup())
        ):

            if newChannel != self.snap_channel_comboBox.currentText():
                with blockSignals(self.snap_channel_comboBox):
                    self.snap_channel_comboBox.setCurrentText(newChannel)
            else:
                self._mmc.setConfig(
                    self._mmc.getChannelGroup(), newChannel
                )  # -> configSet

            self._change_channel_cbox_in_table(self._mmc.getChannelGroup(), newChannel)

    def _change_channel_cbox_in_table(self, channel_group: str, channel_preset: str):
        for row in range(self.table.shape[0]):
            group, wdg = self.table.data[row]
            if group == channel_group and wdg.get_value() != channel_preset:
                with blockSignals(wdg.native):
                    wdg.value = channel_preset  # -> configSet
                break

    def _change_objective_main_gui(self, objective: str):

        if self.objective_comboBox.count() <= 0:
            return
        if self.objectives_device == "":
            return

        if self.objectives_cfg and objective in list(
            self._mmc.getAvailableConfigs(self.objectives_cfg)
        ):

            if objective != self.objective_comboBox.currentText():
                with blockSignals(self.objective_comboBox):
                    self.objective_comboBox.setCurrentText(objective)
            else:
                self._mmc.setConfig(
                    self.objectives_cfg, self.objective_comboBox.currentText()
                )  # -> configSet

            self._change_objective_cbox_in_table(self.objectives_cfg, objective)

        else:
            objective_list = [
                self.objective_comboBox.itemText(i)
                for i in range(self.objective_comboBox.count())
            ]
            if objective in objective_list:
                self._mmc.setProperty(
                    self.objectives_device,
                    "Label",
                    self.objective_comboBox.currentText(),
                )  # -> propertyChanged

        self._update_pixel_size()

    def _change_objective_cbox_in_table(
        self, objective_group: str, objective_preset: str
    ):
        for row in range(self.table.shape[0]):
            group, wdg = self.table.data[row]
            if group == objective_group and wdg.get_value() != objective_preset:
                with blockSignals(wdg.native):
                    wdg.value = objective_preset  # -> configSet
                break

    def _on_xy_stage_position_changed(self, name, x, y):
        self.x_lineEdit.setText(f"{x:.1f}")
        self.y_lineEdit.setText(f"{y:.1f}")

    def _on_stage_position_changed(self, name, value):
        if "z" in name.lower():  # hack
            self.z_lineEdit.setText(f"{value:.1f}")

    def stage_x_left(self):
        self._mmc.setRelativeXYPosition(-float(self.xy_step_size_SpinBox.value()), 0.0)
        if self.snap_on_click_xy_checkBox.isChecked():
            self.snap()

    def stage_x_right(self):
        self._mmc.setRelativeXYPosition(float(self.xy_step_size_SpinBox.value()), 0.0)
        if self.snap_on_click_xy_checkBox.isChecked():
            self.snap()

    def stage_y_up(self):
        self._mmc.setRelativeXYPosition(
            0.0,
            float(self.xy_step_size_SpinBox.value()),
        )
        if self.snap_on_click_xy_checkBox.isChecked():
            self.snap()

    def stage_y_down(self):
        self._mmc.setRelativeXYPosition(
            0.0,
            -float(self.xy_step_size_SpinBox.value()),
        )
        if self.snap_on_click_xy_checkBox.isChecked():
            self.snap()

    def stage_z_up(self):
        self._mmc.setRelativeXYZPosition(
            0.0, 0.0, float(self.z_step_size_doubleSpinBox.value())
        )
        if self.snap_on_click_z_checkBox.isChecked():
            self.snap()

    def stage_z_down(self):
        self._mmc.setRelativeXYZPosition(
            0.0, 0.0, -float(self.z_step_size_doubleSpinBox.value())
        )
        if self.snap_on_click_z_checkBox.isChecked():
            self.snap()

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

        if self.tabWidget.currentIndex() != 1:
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

            ch_group = self._mmc.getChannelGroup()
            if ch_group:
                self._mmc.setConfig(ch_group, self.snap_channel_comboBox.currentText())
            else:
                return

            self.start_live()
            self.live_Button.setIcon(CAM_STOP_ICON)
        else:
            self.stop_live()
            self.live_Button.setIcon(CAM_ICON)
