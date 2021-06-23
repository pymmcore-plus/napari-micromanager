from __future__ import annotations

from datetime import datetime
from logging import warning

from os import PRIO_PGRP

from pathlib import Path
from re import escape, split
import time
from typing import Sequence, TYPE_CHECKING
from napari.components import layerlist
from napari.layers.base.base import Layer

import tifffile
import tempfile

import napari
import numpy as np
from pymmcore_remote import RemoteMMCore
from pymmcore_remote.qcallbacks import QCoreCallback
from qtpy import QtWidgets as QtW
from qtpy import uic
from qtpy.QtCore import QSize, QTimer
from qtpy.QtGui import QIcon
from tifffile.tifffile import sequence

from ._util import extend_array_for_index, get_filename, check_filename
from .explore_sample import ExploreSample
from .multid_widget import MultiDWidget

import warnings


if TYPE_CHECKING:
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
    exp_spinBox: QtW.QSpinBox
    snap_Button: QtW.QPushButton
    live_Button: QtW.QPushButton
    max_val_lineEdit: QtW.QLineEdit
    min_val_lineEdit: QtW.QLineEdit
    move_to: QtW.QGroupBox
    move_to_main_Button: QtW.QPushButton
    x_lineEdit_main: QtW.QLineEdit
    y_lineEdit_main: QtW.QLineEdit

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
    def __init__(self, viewer: napari.viewer.Viewer):
        super().__init__()
        self.setup_ui()

        self.viewer = viewer
        self.streaming_timer = None
        
        # create connection to mmcore server
        self._mmc = RemoteMMCore()
        sig = QCoreCallback()
        self._mmc.register_callback(sig)

        # tab widgets
        self.mda = MultiDWidget(self._mmc)
        self.explorer = ExploreSample(self._mmc)
        self.tabWidget.addTab(self.mda, "Multi-D Acquisition")
        self.tabWidget.addTab(self.explorer, "Sample Explorer")

        self.x_lineEdit_main.setText(str(None))
        self.y_lineEdit_main.setText(str(None))
        self.explorer.x_lineEdit.setText(str(None))
        self.explorer.y_lineEdit.setText(str(None))

        # connect mmcore signals
            #mda
        sig.MDAStarted.connect(self.mda._on_mda_started)
        sig.MDAFinished.connect(self.mda._on_mda_finished)
            #mainwindow
        sig.MDAStarted.connect(self._on_mda_started)
        sig.MDAFinished.connect(self._on_mda_finished)

        sig.MDAPauseToggled.connect(
            lambda p: self.mda.pause_Button.setText("GO" if p else "PAUSE")
        )
        sig.systemConfigurationLoaded.connect(self._on_system_configuration_loaded)
        sig.XYStagePositionChanged.connect(self._on_xy_stage_position_changed)
        sig.stagePositionChanged.connect(self._on_stage_position_changed)
        sig.MDAFrameReady.connect(self._on_mda_frame)

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

        self.move_to_main_Button.clicked.connect(self.move_to_position)
        self.x_lineEdit_main.setText(str(None))
        self.y_lineEdit_main.setText(str(None))
        self.explorer.x_lineEdit.setText(str(None))
        self.explorer.y_lineEdit.setText(str(None))

        # connect comboBox
        self.objective_comboBox.currentIndexChanged.connect(self.change_objective)
        self.bit_comboBox.currentIndexChanged.connect(self.bit_changed)
        self.bin_comboBox.currentIndexChanged.connect(self.bin_changed)


        @self.viewer.mouse_drag_callbacks.append
        def get_event(viewer, event):
            
            if self._mmc.getPixelSizeUm() > 0:

                w = self._mmc.getROI(self._mmc.getCameraDevice())[2] 
                h = self._mmc.getROI(self._mmc.getCameraDevice())[3]

                x = viewer.cursor.position[-1] * self._mmc.getPixelSizeUm()
                y = viewer.cursor.position[-2] * self._mmc.getPixelSizeUm() * (- 1)

                x = x - ((w/2) * self._mmc.getPixelSizeUm())
                y = y - ((h/2) * self._mmc.getPixelSizeUm() * (- 1))

            else:
                x = None
                y = None

            self.x_lineEdit_main.setText(str(x))
            self.y_lineEdit_main.setText(str(y))
            self.explorer.x_lineEdit.setText(str(x))
            self.explorer.y_lineEdit.setText(str(y))
        
    def enable_gui(self):
        self.objective_groupBox.setEnabled(True)
        self.camera_groupBox.setEnabled(True)
        self.XY_groupBox.setEnabled(True)
        self.Z_groupBox.setEnabled(True)
        self.snap_live_tab.setEnabled(True)
        self.snap_live_tab.setEnabled(True)

    def disable_gui(self):
        self.objective_groupBox.setEnabled(False)
        self.camera_groupBox.setEnabled(False)
        self.XY_groupBox.setEnabled(False)
        self.Z_groupBox.setEnabled(False)
        self.snap_live_tab.setEnabled(False)
        self.snap_live_tab.setEnabled(False)


    def move_to_position(self):

        move_to_x = self.x_lineEdit_main.text()
        move_to_y = self.y_lineEdit_main.text()

        if move_to_x == "None" and move_to_y == "None":
            warnings.warn('PIXEL SIZE NOT SET.')
        else:
            move_to_x = float(move_to_x) 
            move_to_y = float(move_to_y)
            self._mmc.setXYPosition(float(move_to_x), float(move_to_y))


    def delete_layer(self, name):
        layer_set = {str(layer) for layer in self.viewer.layers}
        if name in layer_set:
            self.viewer.layers.remove(name)
        layer_set.clear()


    def _on_mda_started(self, sequence: useq.MDASequence):
        """"create temp folder and block gui when mda starts."""
        
        self.viewer.grid.enabled = False

        self.temp_folder = tempfile.TemporaryDirectory(None, str(sequence.uid))

        self.mda.disable_mda_groupbox()
        self.explorer.disable_explorer_groupbox()
        self.disable_gui()

    def _on_mda_frame(self, image: np.ndarray, event: useq.MDAEvent):

        seq = event.sequence

        #get the index of the incoming image
        if self.mda.checkBox_split_channels.isChecked():
            im_idx = tuple(event.index[k] for k in seq.axis_order if ((k in event.index) and (k != 'c')))
        else:
            im_idx = tuple(event.index[k] for k in seq.axis_order if k in event.index)

        try:
            #see if we already have a layer with this sequence
            if self.mda.checkBox_split_channels.isChecked():
                layer = next(
                    x for x in self.viewer.layers if x.metadata.get("ch_id") == \
                        (str(seq.uid) + f'_{event.channel.config}_idx{event.index["c"]}'))
            else:
                layer = next(
                    x for x in self.viewer.layers if x.metadata.get("uid") == seq.uid
                )

            #make sure array shape contains im_idx, or pad with zeros
            new_array = extend_array_for_index(layer.data, im_idx)

            #add the incoming index at the appropriate index
            new_array[im_idx] = image
            
            #set layer data
            layer.data = new_array

            for a, v in enumerate(im_idx):
                self.viewer.dims.set_point(a, v)

            #save each image in the temp folder
            if self.mda.checkBox_split_channels.isChecked():
                image_name = f'{event.channel.config}_idx{event.index["c"]}.tif'
            else:
                image_name = f'{im_idx}.tif'
            
            if hasattr(self, 'temp_folder'): 
                savefile = Path(self.temp_folder.name) / image_name
                tifffile.tifffile.imsave(str(savefile), image, imagej=True)
            
        except StopIteration:
            
            if self.mda.save_groupBox.isChecked():

                file_name = self.mda.fname_lineEdit.text()

                if self.mda.checkBox_split_channels.isChecked():
                    layer_name = f"{file_name}_[{event.channel.config}_idx{event.index['c']}]_{datetime.now().strftime('%H:%M:%S')}"
                else:
                    layer_name = f"{file_name}_{datetime.now().strftime('%H:%M:%S')}"
            
            else:
                if self.mda.checkBox_split_channels.isChecked():
                    layer_name = f"Experiment_[{event.channel.config}-idx{event.index['c']}]_{datetime.now().strftime('%H:%M:%S')}"
                else:
                    layer_name = f"Experiment_{datetime.now().strftime('%H:%M:%S')}"
                    
            _image = image[(np.newaxis,) * len(seq.shape)]
            layer = self.viewer.add_image(_image, name=layer_name)
            
            labels = [i for i in seq.axis_order if i in event.index] + ["y", "x"]

            self.viewer.dims.axis_labels = labels

            #add metadata to layer
            layer.metadata["useq_sequence"] = seq
            layer.metadata["uid"] = seq.uid
            
            if self.mda.checkBox_split_channels.isChecked():
                layer.metadata["ch_id"] = str(seq.uid) + f'_{event.channel.config}_idx{event.index["c"]}'
            
            #save first image in the temp folder
            if self.mda.checkBox_split_channels.isChecked():
                image_name = f'{event.channel.config}_idx{event.index["c"]}.tif'
            else:
                image_name = f'{im_idx}.tif'
                
            if hasattr(self, 'temp_folder'):  
                savefile = Path(self.temp_folder.name) / image_name
                tifffile.tifffile.imsave(str(savefile), image, imagej=True)

    def _on_mda_finished(self, sequence: useq.MDASequence):
        """Save layer and add increment to save name."""

        if self.mda.save_groupBox.isChecked():

            fname =  self.mda.fname_lineEdit.text()

            save_path = Path(self.dir_lineEdit.text())

            if self.mda.checkBox_split_channels.isChecked():
                #Save individual channel layer(s).

                #create folder to save individual channel layer(s).
                fname = check_filename(fname, save_path)
                
                folder_name = Path(save_path) / fname

                try:
                    Path(folder_name).mkdir(parents=True, exist_ok=False)
                except FileExistsError:
                    pass
                
                uid = sequence.uid

                if self.mda.checkBox_save_pos.isChecked():
                #save each position and channel in a separate file.

                    for p in range(len(sequence.stage_positions)):
                        
                        pos_num = '{0:03}'.format(int(p))
                        folder_path = Path(folder_name) / f'{fname}_Pos{pos_num}'

                        try:
                            Path(folder_path).mkdir(parents=True, exist_ok=False)
                        except FileExistsError:
                            pass

                        for i in self.viewer.layers:

                            if 'ch_id' in i.metadata and \
                                str(uid) in i.metadata.get('ch_id'):
                            
                                    ch_id_info = i.metadata.get('ch_id')

                                    new_layer_name = ch_id_info.replace(str(uid), fname)

                                    fname_pos = f'{new_layer_name}_[p{pos_num}]'
                                    
                                    if len(sequence.time_plan) > 0 and \
                                        sequence.axis_order[0] == 't':
                                            layer_p = i.data[:,p]   
                                    else:
                                        layer_p = i.data[p,:]

                                    save_path_ch = folder_path / f'{fname_pos}.tif'
                    
                                    #TODO: astype 'uint_' dependimg on camera bit depth selected
                                    tifffile.tifffile.imsave(str(save_path_ch), layer_p.astype('uint16'), imagej=True)                    
               
                else:
                    #save each channel layer.
                    for i in self.viewer.layers:
                        
                        if 'ch_id' in i.metadata and \
                            str(uid) in i.metadata.get('ch_id'):
                            
                                ch_id_info = i.metadata.get('ch_id')
                                new_layer_name = ch_id_info.replace(str(uid), fname)
                            
                                save_path_ch = folder_name / f'{new_layer_name}.tif'

                                #TODO: astype 'uint_' dependimg on camera bit depth selected
                                i.data = i.data.astype('uint16')
                                i.save(str(save_path_ch))

                #update filename in mda.fname_lineEdit for the next aquisition.
                fname = get_filename(fname, save_path)
                self.mda.fname_lineEdit.setText(fname)

            else:
                try:
                    active_layer = next(l for l in self.viewer.layers if l.metadata.get('uid') == sequence.uid)
                except StopIteration:
                    raise IndexError("could not find layer corresponding to sequence")

                fname = check_filename(fname, save_path)

                if self.mda.checkBox_save_pos.isChecked():
                #save each position in a separate file

                    folder_name = f'{fname}_Pos'
                    folder_path = Path(save_path) / folder_name

                    try:
                        Path(folder_path).mkdir(parents=True, exist_ok=False)
                    except FileExistsError:
                        pass

                    for p in range(len(sequence.stage_positions)):
                        pos_num = '{0:03}'.format(int(p))
                        fname_pos = f'{fname}_[p{pos_num}]'

                        if len(sequence.time_plan) > 0 and \
                            sequence.axis_order[0] == 't':
                                layer_p = active_layer.data[:,p]   
                        else:
                            layer_p = active_layer.data[p,:]

                        name = fname_pos + '.tif'
                        save_path_pos = Path(folder_path) / name
                        #TODO: astype 'uint_' dependimg on camera bit depth selected
                        tifffile.tifffile.imsave(str(save_path_pos), layer_p.astype('uint16'), imagej=True)                    

                else:
                    #TODO: astype 'uint_' dependimg on camera bit depth selected
                    active_layer.data = active_layer.data.astype('uint16')
                    active_layer.save(str(save_path / fname))
                
                #update filename in mda.fname_lineEdit for the next aquisition.
                fname = get_filename(fname, save_path)
                self.mda.fname_lineEdit.setText(fname)


        #for sample explorer
        if sequence.extras == 'sample_explorer':

            w = self._mmc.getROI(self._mmc.getCameraDevice())[2] 
            h = self._mmc.getROI(self._mmc.getCameraDevice())[3]

            try:
                explorer_layer = next(l for l in self.viewer.layers if l.metadata.get('uid') == sequence.uid)
            except StopIteration:
                raise IndexError("could not find layer corresponding to sequence") 

            if self.explorer.save_explorer_groupBox.isChecked():

                fname =  self.explorer.fname_explorer_lineEdit.text()
                save_path = Path(self.explorer.dir_explorer_lineEdit.text())

                fname = check_filename(fname, save_path)

                folder_name = Path(save_path) / fname

                try:
                    Path(folder_name).mkdir(parents=True, exist_ok=False)
                    print('MAKE DIR')
                except FileExistsError:
                    pass

                #update filename in mda.fname_lineEdit for the next aquisition.
                fname = get_filename(fname, save_path)
                self.explorer.fname_explorer_lineEdit.setText(fname)

            #split stack and translate images depending on xy position (in pixel)
            for f in range(len(explorer_layer.data)):

                x = sequence.stage_positions[f].x / self._mmc.getPixelSizeUm() 
                y = sequence.stage_positions[f].y / self._mmc.getPixelSizeUm() * (- 1)

                x = x - ((w/2) * self._mmc.getPixelSizeUm())
                y = y - ((h/2) * self._mmc.getPixelSizeUm() * (- 1))

                z = 0
                
                framename = f"Pos{'{0:03}'.format(int(f))}"

                frame = self.viewer.add_image(explorer_layer.data[f], \
                    name = framename, translate=(z,y,x), opacity=0.5)

                frame.metadata['frame'] = f"frame_pos{'{0:03}'.format(int(f))}"
                frame.metadata['stage_position'] = sequence.stage_positions[f]
                frame.metadata['uid_p'] = str(sequence.uid) + f"_frame_pos{'{0:03}'.format(int(f))}"
                
                if self.explorer.save_explorer_groupBox.isChecked():
                    #TODO: astype 'uint_' dependimg on camera bit depth selected
                    frame.data = frame.data.astype('uint16')
                    frame.save(str(folder_name / f'{framename}_{fname}'))

            self.viewer.layers.remove(explorer_layer)

            self.viewer.reset_view()

        if hasattr(self, 'temp_folder'):
            self.temp_folder.cleanup()
            
        #reactivate gui when mda finishes.
        self.mda.enable_mda_groupbox()
        self.explorer.enable_explorer_groupbox()
        self.enable_gui()



    def browse_cfg(self):
        self._mmc.unloadAllDevices()  # unload all devicies
        print(f"Loaded Devicies: {self._mmc.getLoadedDevices()}")

        # clear spinbox/combobox
        self.objective_comboBox.clear()
        self.bin_comboBox.clear()
        self.bit_comboBox.clear()
        self.snap_channel_comboBox.clear()

        file_dir = QtW.QFileDialog.getOpenFileName(self, "", "⁩", "cfg(*.cfg)")
        self.cfg_LineEdit.setText(str(file_dir[0]))
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
            self.bin_comboBox.clear()
            bin_opts = self._mmc.getAllowedPropertyValues(cam_device, "Binning")
            self.bin_comboBox.addItems(bin_opts)
            self.bin_comboBox.setCurrentText(
                self._mmc.getProperty(cam_device, "Binning")
            )

        if "PixelType" in cam_props:
            self.bit_comboBox.clear()
            px_t = self._mmc.getAllowedPropertyValues(cam_device, "PixelType")
            self.bit_comboBox.addItems(px_t)
            if "16" in px_t:
                self.bit_comboBox.setCurrentText("16bit")
                self._mmc.setProperty(cam_device, "PixelType", "16bit")

    def _refresh_objective_options(self):
        if "Objective" in self._mmc.getLoadedDevices():
            self.objective_comboBox.clear()
            self.objective_comboBox.addItems(self._mmc.getStateLabels("Objective"))

    def _refresh_channel_list(self):
        if "Channel" in self._mmc.getAvailableConfigGroups():
            self.snap_channel_comboBox.clear()
            self.explorer.scan_channel_comboBox.clear()
            self.mda.clear_channel()
            channel_list = list(self._mmc.getAvailableConfigs("Channel"))
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

    def _on_xy_stage_position_changed(self, name, x, y):
        self.x_lineEdit.setText(f"{x:.1f}")
        self.y_lineEdit.setText(f"{y:.1f}")
        self.x_lineEdit_main.setText(str(x))
        self.y_lineEdit_main.setText(str(y))
        self.explorer.x_lineEdit.setText(str(x))
        self.explorer.y_lineEdit.setText(str(y))

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
        if not self.objective_comboBox.count() > 0:
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

        magnification = None
        # get magnification info from the objective
        for i in range(len(curr_obj_name)):
            character = curr_obj_name[i]
            if character in ["X", "x"]:
                if i <= 3:
                    magnification_string = curr_obj_name[:i]
                    magnification = int(magnification_string)
                    print(f"Current Magnification: {magnification}X")
                else:
                    warnings.warn("MAGNIFICATION NOT SET, STORE OBJECTIVES NAME "
                        "STARTING WITH e.g. 100X or 100x.")

        # get and set image pixel sixe (x,y) for the current pixel size Config
        if magnification is not None:
            self.image_pixel_size = self.px_size_doubleSpinBox.value() / magnification
            self._mmc.setPixelSizeUm(
                self._mmc.getCurrentPixelSizeConfig(), self.image_pixel_size
            )
            print(f"Current Pixel Size in µm: {self._mmc.getPixelSizeUm()}")

    def update_viewer(self, data=None):
        if data is None:
            try:
                data = self._mmc.popNextImage()
            except (RuntimeError, IndexError):
                # circular buffer empty
                return
        try:
            preview_layer = self.viewer.layers["preview"]
            preview_layer.data = data
        except KeyError:
            preview_layer = self.viewer.add_image(data, name="preview")
            
        self.max_val_lineEdit.setText(str(np.max(preview_layer.data)))
        self.min_val_lineEdit.setText(str(np.min(preview_layer.data)))

        if self._mmc.getPixelSizeUm() > 0:
            x = self._mmc.getXPosition() / self._mmc.getPixelSizeUm()
            y = self._mmc.getYPosition()/ self._mmc.getPixelSizeUm() * (- 1)
            self.viewer.layers["preview"].translate = (y,x)
        
        else:
            self.x_lineEdit_main.setText(str(None))
            self.y_lineEdit_main.setText(str(None))
            self.explorer.x_lineEdit.setText(str(None))
            self.explorer.y_lineEdit.setText(str(None))

        if self.streaming_timer is None:
            self.viewer.reset_view()


    def snap(self):
        self.stop_live()
        self._mmc.setExposure(int(self.exp_spinBox.value()))

        ch_group = self._mmc.getChannelGroup() or "Channel"
        self._mmc.setConfig(ch_group, self.snap_channel_comboBox.currentText())
        
        self._mmc.snapImage()
        self.update_viewer(self._mmc.getImage())

    def start_live(self):
        self._mmc.startContinuousSequenceAcquisition(int(self.exp_spinBox.value()))
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
            
            ch_group = self._mmc.getChannelGroup() or "Channel"
            self._mmc.setConfig(ch_group, self.snap_channel_comboBox.currentText())

            self.start_live()
            self.live_Button.setIcon(CAM_STOP_ICON)
        else:
            self.stop_live()
            self.live_Button.setIcon(CAM_ICON)
