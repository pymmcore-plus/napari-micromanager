import os
import sys
from pathlib import Path
import numpy as np
from PyQt5 import QtWidgets as QtW
from qtpy import uic
import time
from qtpy.QtWidgets import QFileDialog

from mmcore_pymmcore import MMCore


UI_FILE = str(Path(__file__).parent / "multid_gui.ui")

mmcore = MMCore()

class MultiDWidget(QtW.QWidget):
    # The UI_FILE above contains these objects:
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

    def uncheck_all(self):#Enable the gui (when .cfg is loaded)
        self.save_groupBox.setChecked(False)
        self.channel_groupBox.setChecked(False)
        self.time_groupBox.setChecked(False)
        self.stack_groupBox.setChecked(False)
        self.stage_pos_groupBox.setChecked(False)


    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(UI_FILE, self)
        
        
        #connect groupbox state change
        self.save_groupBox.toggled.connect(self.enable_run_Button)
        self.channel_groupBox.toggled.connect(self.enable_run_Button)
        self.time_groupBox.toggled.connect(self.enable_run_Button)
        self.stack_groupBox.toggled.connect(self.enable_run_Button)
        self.stage_pos_groupBox.toggled.connect(self.enable_run_Button)

        #connect buttons
        #self.run_Button.clicked.connect(self.load_cfg)

    def enable_run_Button(self):
        dev_loaded = list(mmcore.getLoadedDevices())
        if len(dev_loaded) > 1:
            self.run_Button.setEnabled(True)
        else:
            self.uncheck_all()


    



    