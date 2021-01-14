import os
import sys
from pathlib import Path
import numpy as np
from PyQt5 import QtWidgets as QtW
from qtpy import uic
from qtpy.QtCore import Qt
import time
from qtpy.QtWidgets import QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5 import QtCore


from mmcore_pymmcore import MMCore

icon_path = Path(__file__).parent/'icons'

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

    # def uncheck_all(self):#Enable the gui (when .cfg is loaded)
    #     self.save_groupBox.setChecked(False)
    #     self.channel_groupBox.setChecked(False)
    #     self.time_groupBox.setChecked(False)
    #     self.stack_groupBox.setChecked(False)
    #     self.stage_pos_groupBox.setChecked(False)


    def __init__(self, *args):
        super().__init__(*args)
        uic.loadUi(UI_FILE, self)

        # self.pos_list = []
        
        #connect buttons      
        self.add_pos_Button.clicked.connect(self.add_position)        
        self.remove_pos_Button.clicked.connect(self.remove_position)
        self.clear_pos_Button.clicked.connect(self.clear_positions)
        self.stage_tableWidget.cellDoubleClicked.connect(self.move_to_position)
        #self.run_Button.clicked.connect(self.load_cfg)

        #button icon
        self.run_Button.setIcon(QIcon(str(icon_path/'play-button_1.svg')))
        self.run_Button.setIconSize(QtCore.QSize(20,20)) 

        #connect groupbox state change
        # self.save_groupBox.toggled.connect(self.enable_run_Button)
        # self.channel_groupBox.toggled.connect(self.enable_run_Button)
        # self.time_groupBox.toggled.connect(self.enable_run_Button)
        # self.stack_groupBox.toggled.connect(self.enable_run_Button)
        # self.stage_pos_groupBox.toggled.connect(self.enable_run_Button)

    # def enable_run_Button(self):
    #     dev_loaded = list(mmcore.getLoadedDevices())
    #     if len(dev_loaded) > 1:
    #         self.acquisition_order_comboBox.setEnabled(True)
    #         self.run_Button.setEnabled(True)
    #     else:
    #         self.uncheck_all()
    #         self.run_Button.setEnabled(False)

    def add_position(self):
        # get stage x, y ans z coordinate
        # add current xyz pos
        # idx = len(self.pos_list)

        x = mmcore.getXPosition()
        y = mmcore.getYPosition()
        z = mmcore.getPosition("Z_Stage")

        x_txt = QtW.QTableWidgetItem(str(x))
        y_txt = QtW.QTableWidgetItem(str(y))
        z_txt = QtW.QTableWidgetItem(str(z))
        x_txt.setTextAlignment(Qt.AlignHCenter|Qt.AlignVCenter)
        y_txt.setTextAlignment(Qt.AlignHCenter|Qt.AlignVCenter)
        z_txt.setTextAlignment(Qt.AlignHCenter|Qt.AlignVCenter)

        idx = self.stage_tableWidget.rowCount()
        self.stage_tableWidget.insertRow(idx)

        self.stage_tableWidget.setItem(idx,0,QtW.QTableWidgetItem(x_txt))
        self.stage_tableWidget.setItem(idx,1,QtW.QTableWidgetItem(y_txt))
        self.stage_tableWidget.setItem(idx,2,QtW.QTableWidgetItem(z_txt))

    def remove_position(self):
        # remove selected position
        row = self.stage_tableWidget.currentRow()
        self.stage_tableWidget.removeRow(row)

    def clear_positions(self):
        # clear all positions
        self.stage_tableWidget.clearContents()
        self.stage_tableWidget.setRowCount(0)
    
    def move_to_position(self):
        curr_row = self.stage_tableWidget.currentRow()
        # print('---')
        # print(f'curr_row: {curr_row}')
        #if curr_row != -1:  
        x_val = self.stage_tableWidget.item(curr_row, 0).text()
        y_val = self.stage_tableWidget.item(curr_row, 1).text()
        z_val = self.stage_tableWidget.item(curr_row, 2).text()
        # print(f'x: {x_val}')
        # print(f'y: {y_val}')
        # print(f'z: {z_val}')
        mmcore.setXYPosition(float(x_val),float(y_val))
        mmcore.setPosition("Z_Stage", float(z_val)) 

    
           






    def save_multi_d_acq(self):
        #set the directory
        self.dir = QFileDialog(self)
        self.dir.setFileMode(QFileDialog.DirectoryOnly)
        self.save_dir = QFileDialog.getExistingDirectory(self.dir)
        self.dir_rec_lineEdit.setText(self.save_dir)
        self.parent_path = Path(self.save_dir)



    def run_mda(self):
        dev_loaded = list(mmcore.getLoadedDevices())
        if len(dev_loaded) > 1:
            
            pass
       
       
        else:
           print('Load a configuration first!')
           #add dialog pop up window








    #in run button add 
    


    



    