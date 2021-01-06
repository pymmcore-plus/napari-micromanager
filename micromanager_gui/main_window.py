import sys

#from qtpy import QtWidgets as QtW
from PyQt5 import QtWidgets as QtW

from qtpy import uic

from pathlib import Path
import pymmcore
from qtpy.QtWidgets import QFileDialog



UI_FILE = str(Path(__file__).parent / "micromanager_gui.ui")
DEFAULT_CFG_FILE = str((Path(__file__).parent / "demo_config.cfg").absolute())#look for the 'demo_config.cfg' in the parent folder 
DEFAULT_CFG_NAME = 'Demo.cfg'

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

    channel_comboBox: QtW.QComboBox
    exp_spinBox: QtW.QSpinBox
    snap_Button: QtW.QPushButton
    live_Button: QtW.QPushButton


    def __init__(self, viewer):
        super().__init__()

        self.viewer = viewer

        uic.loadUi(UI_FILE, self)#load QtDesigner .ui file

        self.cfg_LineEdit.setText(DEFAULT_CFG_NAME)#fill cfg line with

        #connect buttons
        self.load_cgf_Button.clicked.connect(self.load_cfg)
        self.browse_cfg_Button.clicked.connect(self.browse_cfg)


    def browse_cfg(self):
        self.cfg_file = QFileDialog.getOpenFileName(self, '', '⁩', 'cfg(*.cfg)')
        self.cfg_LineEdit.setText(self.cfg_file)


    def load_cfg(self):
        #to be added: reset all!!!!!!!!
        cfg_file = self.cfg_LineEdit.text()
        if cfg_file == DEFAULT_CFG_NAME:
            cfg_file = DEFAULT_CFG_FILE
            print('demo')

        try
            mmcore.loadSystemConfiguration(cfg_file) #load the configuration file
        except KeyError:
            print('No Corrected_Neuron_ROI_ + (self.filename) layer')
            
        mmcore.setPosition("Z_Stage", 50)  # to test
        print('cfg loaded')



