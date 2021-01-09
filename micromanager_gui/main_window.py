import sys
import os
import time

#from qtpy import QtWidgets as QtW
from PyQt5 import QtWidgets as QtW

from qtpy import uic

from pathlib import Path
import pymmcore
from qtpy.QtWidgets import QFileDialog

from PyQt5.QtGui import QIcon
from PyQt5 import QtCore

import numpy as np


#dir_path = Path(__file__).parent
icon_path = Path(__file__).parent/'icons'


UI_FILE = str(Path(__file__).parent / "micromanager_gui.ui")
DEFAULT_CFG_FILE = str((Path(__file__).parent / "demo_config.cfg").absolute())#look for the 'demo_config.cfg' in the parent folder 
DEFAULT_CFG_NAME = 'demo.cfg'

mmcore = pymmcore.CMMCore()#assign mmcore

#find micromanager path
def find_micromanager():
    if sys.platform == "darwin":
        return str(next(Path("/Applications/").glob("Micro-Manager*")))
    raise RuntimeError(f"Not configured for OS: {sys.platform}")

mmcore.setDeviceAdapterSearchPaths([find_micromanager()])#set the micromanager path


class MainWindow(QtW.QMainWindow):
    
    # The UI_FILE above contains these objects:
    cfg_LineEdit: QtW.QLineEdit
    browse_cfg_Button: QtW.QPushButton
    load_cgf_Button: QtW.QPushButton

    objective_groupBox: QtW.QGroupBox
    objective_comboBox: QtW.QComboBox
    
    camera_groupBox: QtW.QGroupBox
    bin_comboBox: QtW.QComboBox
    bit_comboBox: QtW.QComboBox

    camera_groupBox: QtW.QGroupBox
    x_lineEdit: QtW.QLineEdit
    y_lineEdit: QtW.QLineEdit
    z_lineEdit: QtW.QLineEdit
    pos_update_Button: QtW.QPushButton

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

    snap_channel_comboBox: QtW.QComboBox
    exp_spinBox: QtW.QSpinBox
    snap_Button: QtW.QPushButton
    live_Button: QtW.QPushButton

    max_val_lineEdit: QtW.QLineEdit
    min_val_lineEdit: QtW.QLineEdit

    save_groupBox: QtW.QGroupBox
    fname_lineEdit: QtW.QLineEdit
    dir_lineEdit: QtW.QLineEdit
    browse_save_Button: QtW.QPushButton

    channel_groupBox: QtW.QGroupBox
    channel_tableWidget: QtW.QTableWidget
    add_ch_Button: QtW.QPushButton
    clear_ch_Button: QtW.QPushButton
    remove_ch_Button: QtW.QPushButton

    time_groupBox: QtW.QGroupBox
    frames_spinBox: QtW.QSpinBox
    interval_spinBox: QtW.QSpinBox
    time_comboBox: QtW.QComboBox

    stack_groupBox: QtW.QGroupBox
    step_spinBox: QtW.QSpinBox
    step_size_doubleSpinBox: QtW.QDoubleSpinBox
    
    stage_pos_groupBox: QtW.QGroupBox
    stage_tableWidget: QtW.QTableWidget
    add_pos_Button: QtW.QPushButton
    clear_pos_Button: QtW.QPushButton
    remove_pos_Button: QtW.QPushButton

    acquisition_order_comboBox: QtW.QComboBox
    run_Button: QtW.QPushButton



    def enable(self):#Enable the gui (when .cfg is loaded)
        self.objective_comboBox.setEnabled(True)
        self.bin_comboBox.setEnabled(True)
        self.bit_comboBox.setEnabled(True)
        self.pos_update_Button.setEnabled(True)
        self.xy_step_size_SpinBox.setEnabled(True)
        self.z_step_size_doubleSpinBox.setEnabled(True)
        self.left_Button.setEnabled(True)
        self.right_Button.setEnabled(True)
        self.y_up_Button.setEnabled(True)
        self.y_down_Button.setEnabled(True)
        self.up_Button.setEnabled(True)
        self.down_Button.setEnabled(True)
        self.snap_channel_comboBox.setEnabled(True)
        self.exp_spinBox.setEnabled(True)
        self.snap_Button.setEnabled(True)
        self.live_Button.setEnabled(True)
        self.save_groupBox.setEnabled(True)
        self.channel_groupBox.setEnabled(True)
        self.stage_pos_groupBox.setEnabled(True)
        self.time_groupBox.setEnabled(True)
        self.stack_groupBox.setEnabled(True)
        self.acquisition_order_comboBox.setEnabled(True)
        self.run_Button.setEnabled(True)
        
    def disable(self):#Disable the gui (if .cfg is not loaded)
        self.objective_comboBox.setEnabled(False)
        self.bin_comboBox.setEnabled(False)
        self.bit_comboBox.setEnabled(False)
        self.pos_update_Button.setEnabled(False)
        self.xy_step_size_SpinBox.setEnabled(False)
        self.z_step_size_doubleSpinBox.setEnabled(False)
        self.left_Button.setEnabled(False)
        self.right_Button.setEnabled(False)
        self.y_up_Button.setEnabled(False)
        self.y_down_Button.setEnabled(False)
        self.up_Button.setEnabled(False)
        self.down_Button.setEnabled(False)
        self.snap_channel_comboBox.setEnabled(False)
        self.exp_spinBox.setEnabled(False)
        self.snap_Button.setEnabled(False)
        self.live_Button.setEnabled(False)
        self.save_groupBox.setEnabled(False)
        self.channel_groupBox.setEnabled(False)
        self.stage_pos_groupBox.setEnabled(False)
        self.time_groupBox.setEnabled(False)
        self.stack_groupBox.setEnabled(False)
        self.acquisition_order_comboBox.setEnabled(False)
        self.run_Button.setEnabled(False)

        


    def __init__(self, viewer):
        super().__init__()

        self.viewer = viewer
        self.worker = None

        uic.loadUi(UI_FILE, self)#load QtDesigner .ui file

        self.cfg_LineEdit.setText(DEFAULT_CFG_NAME)#fill cfg line with DEFAULT_CFG_NAME ('demo.cfg')

        #connect buttons
        self.load_cgf_Button.clicked.connect(self.load_cfg)
        self.browse_cfg_Button.clicked.connect(self.browse_cfg)

        self.pos_update_Button.clicked.connect(self.update_stage_position)
        self.left_Button.clicked.connect(self.stage_x_left)
        self.right_Button.clicked.connect(self.stage_x_right)
        self.y_up_Button.clicked.connect(self.stage_y_up)
        self.y_down_Button.clicked.connect(self.stage_y_down)
        self.up_Button.clicked.connect(self.stage_z_up)
        self.down_Button.clicked.connect(self.stage_z_down)

        self.snap_Button.clicked.connect(self.snap)
        self.live_Button.clicked.connect(self.toggle_live)

        #button's icon
        #arrows icons
        self.left_Button.setIcon(QIcon(str(icon_path/'left.png')))
        self.left_Button.setIconSize(QtCore.QSize(30,30)) 
        self.right_Button.setIcon(QIcon(str(icon_path/'right.png')))
        self.right_Button.setIconSize(QtCore.QSize(30,30)) 
        self.y_up_Button.setIcon(QIcon(str(icon_path/'up.png')))
        self.y_up_Button.setIconSize(QtCore.QSize(30,30)) 
        self.y_down_Button.setIcon(QIcon(str(icon_path/'down.png')))
        self.y_down_Button.setIconSize(QtCore.QSize(30,30))
        self.up_Button.setIcon(QIcon(str(icon_path/'z_up.png')))
        self.up_Button.setIconSize(QtCore.QSize(30,30)) 
        self.down_Button.setIcon(QIcon(str(icon_path/'z_down.png')))
        self.down_Button.setIconSize(QtCore.QSize(30,30)) 
        #snap/live icons
        #self.snap_Button.setIcon(QIcon(str(icon_path/'camera.png')))
        self.snap_Button.setIcon(QIcon(str(icon_path/'camera_1.svg')))
        self.snap_Button.setIconSize(QtCore.QSize(30,30))
        self.live_Button.setIcon(QIcon(str(icon_path/'vcamera.png')))
        self.live_Button.setIconSize(QtCore.QSize(30,30)) 

        #connect comboBox
        self.objective_comboBox.currentIndexChanged.connect(self.change_objective)

    def browse_cfg(self):
        file_dir = QFileDialog.getOpenFileName(self, '', '⁩', 'cfg(*.cfg)')
        self.new_cfg_file = file_dir[0]
        cfg_name=os.path.basename(str(self.new_cfg_file))
        self.cfg_LineEdit.setText(str(cfg_name))
        self.disable()
        self.max_val_lineEdit.setText("None")
        self.min_val_lineEdit.setText("None")

    def load_cfg(self):
        self.enable()

        #reset combo boxes from previous .cfg settings
        self.objective_comboBox.clear()
        self.bin_comboBox.clear()
        self.bit_comboBox.clear()
        self.snap_channel_comboBox.clear()

        cfg_file = self.cfg_LineEdit.text()
        if cfg_file == DEFAULT_CFG_NAME:
            self.new_cfg_file = DEFAULT_CFG_FILE

        try:
            mmcore.loadSystemConfiguration(self.new_cfg_file) #load the configuration file
        except KeyError:
            print('Select a valid .cfg file.')
    
        # Get Camera Options
        cam_device = mmcore.getCameraDevice()
        cam_props = mmcore.getDevicePropertyNames(cam_device)
        if "Binning" in cam_props:
            bin_opts = mmcore.getAllowedPropertyValues(cam_device, "Binning")
            self.bin_comboBox.addItems(bin_opts)
            self.bin_comboBox.setCurrentText(mmcore.getProperty(cam_device, "Binning"))
        if "BitDepth" in cam_props:
            bit_opts = mmcore.getAllowedPropertyValues(cam_device, "BitDepth")         
            self.bit_comboBox.addItems(sorted(bit_opts, key=lambda x: int(x)))
            self.bit_comboBox.setCurrentText(mmcore.getProperty(cam_device, "BitDepth"))
            if '16' in bit_opts:
                self.bit_comboBox.setCurrentText('16')

        # Get Objective Options
        if "Objective" in mmcore.getLoadedDevices():
            mmcore.setPosition("Z_Stage", 50)#just to test, should be removed
            obj_opts = mmcore.getStateLabels("Objective")
            self.objective_comboBox.addItems(obj_opts)
            self.objective_comboBox.setCurrentText(obj_opts[0])
            
        # Get Channel List
        if "Channel" in mmcore.getAvailableConfigGroups():
            channel_list = list(mmcore.getAvailableConfigs("Channel"))
            self.snap_channel_comboBox.addItems(channel_list)
        else:
            print("Could not find 'Channel' in the ConfigGroups")

        self.update_stage_position()

        self.max_val_lineEdit.setText("None")
        self.min_val_lineEdit.setText("None")

    def update_stage_position(self):
        x = int(mmcore.getXPosition())
        y = int(mmcore.getYPosition())
        z = int(mmcore.getPosition("Z_Stage"))
        self.x_lineEdit.setText(str('%.0f'%x))
        self.y_lineEdit.setText(str('%.0f'%y))
        self.z_lineEdit.setText(str('%.1f'%z))

    def stage_x_left(self):
        xpos = mmcore.getXPosition()
        ypos = mmcore.getYPosition()
        val = int(self.xy_step_size_SpinBox.value())
        mmcore.setXYPosition((xpos + (- val)),ypos) 
        x_new = int(mmcore.getXPosition())
        self.x_lineEdit.setText((str('%.0f'%x_new)))
        mmcore.waitForDevice("XY_Stage")
    
    def stage_x_right(self):
        xpos = mmcore.getXPosition()
        ypos = mmcore.getYPosition()
        val = int(self.xy_step_size_SpinBox.value())
        mmcore.setXYPosition((xpos + val),ypos) 
        x_new = int(mmcore.getXPosition())
        self.x_lineEdit.setText((str('%.0f'%x_new)))
        mmcore.waitForDevice("XY_Stage")

    def stage_y_up(self):
        xpos = mmcore.getXPosition()
        ypos = mmcore.getYPosition()
        val = int(self.xy_step_size_SpinBox.value())
        mmcore.setXYPosition(xpos,(ypos + val)) 
        y_new = int(mmcore.getYPosition())
        self.y_lineEdit.setText((str('%.0f'%y_new)))
        mmcore.waitForDevice("XY_Stage")

    def stage_y_down(self):
        xpos = mmcore.getXPosition()
        ypos = mmcore.getYPosition()
        val = int(self.xy_step_size_SpinBox.value())
        mmcore.setXYPosition(xpos,(ypos + (- val))) 
        y_new = int(mmcore.getYPosition())
        self.y_lineEdit.setText((str('%.0f'%y_new)))
        mmcore.waitForDevice("XY_Stage")
        
    def stage_z_up(self):
        zpos = mmcore.getPosition("Z_Stage")
        z_val = float(self.z_step_size_doubleSpinBox.value())
        mmcore.setPosition("Z_Stage", zpos + z_val) 
        z_new = float(mmcore.getPosition("Z_Stage"))
        self.z_lineEdit.setText((str('%.1f'%z_new)))
        mmcore.waitForDevice("Z_Stage")
    
    def stage_z_down(self):
        zpos = mmcore.getPosition("Z_Stage")
        z_val = float(self.z_step_size_doubleSpinBox.value())
        mmcore.setPosition("Z_Stage", zpos + (-z_val)) 
        z_new = float(mmcore.getPosition("Z_Stage"))
        self.z_lineEdit.setText((str('%.1f'%z_new)))
        mmcore.waitForDevice("Z_Stage")

    def change_objective(self):
        print('changeing objective...')
        currentZ = mmcore.getPosition("Z_Stage")
        print(f"currentZ: {currentZ}")
        mmcore.setPosition("Z_Stage", 0)#set low z position
        mmcore.waitForDevice("Z_Stage")
        self.update_stage_position()
        print(self.objective_comboBox.currentText())
        mmcore.setProperty("Objective", "Label", self.objective_comboBox.currentText())
        mmcore.waitForDevice("Objective")
        print(f"downpos: {mmcore.getPosition('Z_Stage')}")
        mmcore.setPosition("Z_Stage", currentZ)
        mmcore.waitForDevice("Z_Stage")
        print(f"upagain: {mmcore.getPosition('Z_Stage')}")
        print(f"OBJECTIVE: {mmcore.getProperty('Objective', 'Label')}")
        self.update_stage_position()

    def update_viewer(self, data):
        try:
            self.viewer.layers["preview"].data = data
        except KeyError:
            self.viewer.add_image(data, name="preview")

    def snap(self):
        self.stop_live()
        mmcore.setExposure(int(self.exp_spinBox.value()))
        mmcore.setProperty("Cam", "Binning", self.bin_comboBox.currentText())
        mmcore.setProperty("Cam", "PixelType", self.bit_comboBox.currentText() + "bit")
        mmcore.setConfig("Channel", self.snap_channel_comboBox.currentText())
        #mmcore.waitForDevice('')
        mmcore.snapImage()
        self.update_viewer(mmcore.getImage())

        try:
            min_v = np.min(self.viewer.layers["preview"].data)
            self.min_val_lineEdit.setText(str(min_v))
            max_v = np.max(self.viewer.layers["preview"].data)
            self.max_val_lineEdit.setText(str(max_v))
        except KeyError:
            pass
        
    def start_live(self):
        from napari.qt import thread_worker

        @thread_worker(connect={"yielded": self.update_viewer})
        def live_mode():
            import time

            while True:
                mmcore.setExposure(int(self.exp_spinBox.value()))
                mmcore.setProperty("Cam", "Binning", self.bin_comboBox.currentText())
                mmcore.setProperty("Cam", "PixelType", self.bit_comboBox.currentText() + "bit")
                mmcore.setConfig("Channel", self.snap_channel_comboBox.currentText())
                mmcore.snapImage()
                yield mmcore.getImage()

                try:
                    min_v = np.min(self.viewer.layers["preview"].data)
                    self.min_val_lineEdit.setText(str(min_v))
                    max_v = np.max(self.viewer.layers["preview"].data)
                    self.max_val_lineEdit.setText(str(max_v))
                except KeyError:
                    pass

                time.sleep(0.03)

        self.live_Button.setText("Stop")
        self.worker = live_mode()

    def stop_live(self):
        if self.worker:
            self.worker.quit()
            self.worker = None
            self.live_Button.setText("Live")
            
    def toggle_live(self, event=None):
        #same as writing: self.stop_live() if self.worker is not None else self.start_live()
        if self.worker == None:
            self.start_live()
            self.live_Button.setIcon(QIcon(str(icon_path/'vcamera_stop.png')))
            self.live_Button.setIconSize(QtCore.QSize(30,30)) 
        else:
            self.stop_live()
            self.live_Button.setIcon(QIcon(str(icon_path/'vcamera.png')))
            self.live_Button.setIconSize(QtCore.QSize(30,30)) 
        


       
        



