import sys
import os
import time

#from qtpy import QtWidgets as QtW
from PyQt5 import QtWidgets as QtW

from qtpy import uic

from pathlib import Path
import pymmcore
from qtpy.QtWidgets import QFileDialog



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

    objective_comboBox: QtW.QComboBox
    
    bin_comboBox: QtW.QComboBox
    bit_comboBox: QtW.QComboBox

    x_lineEdit: QtW.QLineEdit
    y_lineEdit: QtW.QLineEdit
    z_lineEdit: QtW.QLineEdit
    pos_update_Button: QtW.QPushButton

    snap_channel_comboBox: QtW.QComboBox
    exp_spinBox: QtW.QSpinBox
    snap_Button: QtW.QPushButton
    live_Button: QtW.QPushButton



    def enable(self):#Eeable the gui
        self.objective_comboBox.setEnabled(True)
        self.bin_comboBox.setEnabled(True)
        self.bit_comboBox.setEnabled(True)
        self.pos_update_Button.setEnabled(True)
        self.tabWidget.setEnabled(True)


    def __init__(self, viewer):
        super().__init__()

        self.viewer = viewer
        self.worker = None

        uic.loadUi(UI_FILE, self)#load QtDesigner .ui file

        self.enable()

        self.cfg_LineEdit.setText(DEFAULT_CFG_NAME)#fill cfg line with

        #connect buttons
        self.load_cgf_Button.clicked.connect(self.load_cfg)
        self.browse_cfg_Button.clicked.connect(self.browse_cfg)
        self.pos_update_Button.clicked.connect(self.update_stage_position)

        self.snap_Button.clicked.connect(self.snap)
        self.live_Button.clicked.connect(self.toggle_live)

        #connect comboBox
        self.objective_comboBox.currentIndexChanged.connect(self.change_objective)


        
    def browse_cfg(self):
        file_dir = QFileDialog.getOpenFileName(self, '', '⁩', 'cfg(*.cfg)')
        self.new_cfg_file = file_dir[0]
        cfg_name=os.path.basename(str(self.new_cfg_file))
        self.cfg_LineEdit.setText(str(cfg_name))


    def load_cfg(self):
        #to be added: reset all!!!!!!!!
        #reset combo boxes

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

    def update_stage_position(self):
        x = mmcore.getXPosition()
        y = mmcore.getYPosition()
        z = mmcore.getPosition("Z_Stage")
        self.x_lineEdit.setText(str(x))
        self.y_lineEdit.setText(str(y))
        self.z_lineEdit.setText(str(z))

    def change_objective(self):
        print('changeing objective...')
        currentZ = mmcore.getPosition("Z_Stage")
        print(f"currentZ: {currentZ}")
        mmcore.setPosition("Z_Stage", 0)  # set low z position
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
        # mmcore.waitForDevice('')
        mmcore.snapImage()
        self.update_viewer(mmcore.getImage())

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
                time.sleep(0.03)

        self.live_Button.setText("Stop")
        self.worker = live_mode()

    def stop_live(self):
        if self.worker:
            self.worker.quit()
            self.worker = None
            self.live_Button.setText("Live")

    def toggle_live(self, event=None):
        self.stop_live() if self.worker is not None else self.start_live()
       
        



