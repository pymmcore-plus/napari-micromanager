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
from textwrap import dedent
from skimage import io

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

        self.pos_list = []
        self.pos_stack_array = []

        #connect buttons      
        self.add_pos_Button.clicked.connect(self.add_position)        
        self.remove_pos_Button.clicked.connect(self.remove_position)
        self.clear_pos_Button.clicked.connect(self.clear_positions)
        self.add_ch_Button.clicked.connect(self.add_channel)
        self.remove_ch_Button.clicked.connect(self.remove_channel)
        self.clear_ch_Button.clicked.connect(self.clear_channel)
        
        self.browse_save_Button.clicked.connect(self.set_multi_d_acq_dir)
        self.run_Button.clicked.connect(self.run_multi_d_acq)

        #connect toggle group box
        self.save_groupBox.toggled.connect(self.toggle_run_button)
        self.dir_lineEdit.textChanged.connect(self.toggle_run_button)
        self.fname_lineEdit.textChanged.connect(self.toggle_run_button)

        #connect position table double click
        self.stage_tableWidget.cellDoubleClicked.connect(self.move_to_position)    

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

    def toggle_run_button(self):
        if self.save_groupBox.isChecked():
            if self.dir_lineEdit.text() == '' or self.fname_lineEdit.text()=='':
                self.run_Button.setEnabled(False)
            else:
                self.run_Button.setEnabled(True)

    #add, remove, clear channel table
    def add_channel(self):
        dev_loaded = list(mmcore.getLoadedDevices())
        if len(dev_loaded) > 1:
            idx = self.channel_tableWidget.rowCount()
            self.channel_tableWidget.insertRow(idx)

            #create a combo_box for channels in the table
            self.channel_comboBox = QtW.QComboBox(self)
            self.channel_exp_spinBox = QtW.QSpinBox(self)
            self.channel_exp_spinBox.setRange(0, 10000)
            self.channel_exp_spinBox.setValue(100)
        

            if "Channel" in mmcore.getAvailableConfigGroups():
                channel_list = list(mmcore.getAvailableConfigs("Channel"))
            else:
                print("Could not find 'Channel' in the ConfigGroups")
            self.channel_comboBox.addItems(channel_list)

            self.channel_tableWidget.setCellWidget(idx, 0, self.channel_comboBox)
            self.channel_tableWidget.setCellWidget(idx, 1, self.channel_exp_spinBox)

    def remove_channel(self):
        # remove selected position
        rows = set(r.row() for r in self.channel_tableWidget.selectedIndexes())
        for idx in sorted(rows, reverse=True):
            self.channel_tableWidget.removeRow(idx)

    def clear_channel(self):
        # clear all positions
        self.channel_tableWidget.clearContents()
        self.channel_tableWidget.setRowCount(0)


    #add, remove, clear, move_to positions table
    def add_position(self):
        dev_loaded = list(mmcore.getLoadedDevices())
        if len(dev_loaded) > 1:
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
        rows = set(r.row() for r in self.stage_tableWidget.selectedIndexes())
        for idx in sorted(rows, reverse=True):
            self.stage_tableWidget.removeRow(idx)

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
        print(f'\nStage moved to x:{x_val} y:{y_val} z:{z_val}')
    
    def set_multi_d_acq_dir(self):
        #set the directory
        self.dir = QFileDialog(self)
        self.dir.setFileMode(QFileDialog.DirectoryOnly)
        self.save_dir = QFileDialog.getExistingDirectory(self.dir)
        self.dir_lineEdit.setText(self.save_dir)
        self.parent_path = Path(self.save_dir)

    def acquisition_order(self):
        if self.acquisition_order_comboBox..currentText()=='tp':
            self.run_multi_d_acq()


    def snap_mda(self):
        pass

    def update_viewer(self):
        pass

    def mda_summary_string(self):
        pass

    #create stack array
    def create_stack_array(self, tp, Zp, nC):
        width = mmcore.getROI(mmcore.getCameraDevice())[2]
        height = mmcore.getROI(mmcore.getCameraDevice())[3]
        bitd=mmcore.getProperty(mmcore.getCameraDevice(), "BitDepth")
        dt = f'uint{bitd}'
        mda_stack= np.empty((tp, Zp, nC, height, width), dtype=dt)
        return mda_stack

    def run_multi_d_acq(self):
        dev_loaded = list(mmcore.getLoadedDevices())
        if len(dev_loaded) > 1:
            
            if self.channel_groupBox.isChecked() and self.channel_tableWidget.rowCount()>0:
        
                nC = self.channel_tableWidget.rowCount()

                #timelapse settings
                if self.time_groupBox.isChecked():
                    timepoints = self.frames_spinBox.value()
                    timeinterval = self.interval_spinBox.value()
                    unit = self.time_comboBox.currentText() #min, sec, ms
                    if unit == 'min':
                        timeinterval_unit = timeinterval*60000
                    if unit == 'sec':
                        timeinterval_unit = timeinterval*1000
                    if unit == 'ms':
                        timeinterval_unit = timeinterval
                else:
                    timepoints = 1
                    timeinterval_unit = 0

                #position settings
                self.pos_list.clear()
                print(f'pos_list: {self.pos_list}')
                if self.stage_pos_groupBox.isChecked() and self.stage_tableWidget.rowCount()>0:
                    for row in range(self.stage_tableWidget.rowCount()):
                        x_pos = self.stage_tableWidget.item(row, 0).text()
                        y_pos = self.stage_tableWidget.item(row, 1).text()
                        z_pos = self.stage_tableWidget.item(row, 2).text()
                        self.pos_list.append((x_pos,y_pos,z_pos))
                    print(f'pos_list: {self.pos_list}')
                else:
                    xp = mmcore.getXPosition()
                    yp = mmcore.getYPosition()
                    zp = mmcore.getPosition("Z_Stage")
                    self.pos_list.append((xp,yp,zp))
                    print(f'pos_list: {self.pos_list}')
                
                #z-stack settings
                if self.stack_groupBox.isChecked():
                    n_steps = self.step_spinBox.value()
                    stepsize = self.step_size_doubleSpinBox.value()
                else:
                    n_steps = 1
                    stepsize = 0

                #create stack array
                self.pos_stack_array.clear()
                for _ in range(len(self.pos_list)):
                    pos_stack = self.create_stack_array(timepoints, n_steps, nC) 
                    self.pos_stack_array.append(pos_stack)


                #create save folder in directory
                if self.save_groupBox.isChecked():
                    pl = format(len(self.pos_list), '04d')
                    tl = format(timepoints, '04d')
                    ns = format(n_steps, '04d')
                    nc = format(nC, '04d')

                    save_folder_name = f'{self.fname_lineEdit.text()}_Pos{pl}_t{tl}_z{ns}_c{nc}
                    save_folder = self.parent_path / save_folder_name
                    if save_folder.exists():
                        i = len(os.listdir(self.parent_path))
                        save_folder = Path(f'{save_folder_name}_{i-1}')
                        save_folder_1 = self.parent_path / save_folder
                        os.makedirs(save_folder_1)
                    else:
                        os.makedirs(save_folder)

                #start acquisition

                # header = self._mda_summary_string()
                # print(header)
                
                start_acq_timr = time.perf_counter()
                for t in range(timepoints):
                    print(f"\nt_point: {t}")

                    for position, (x, y, z) in enumerate(self.pos_list):
                        print(f"    \nXY_Pos_n: {position} XY_pos: {x, y} z_start: ({z})")
                        mmcore.setXYPosition(float(x), float(y))
                        mmcore.setPosition("Z_Stage",float(z))
            
                        Bottom_z = mmcore.getPosition("Z_Stage") - ((n_steps / 2) * stepsize)

                        for z_position in range(n_steps):
                            print(f"        \nZ_Pos_n: {z_position} Z: {Bottom_z}")
                            mmcore.setPosition("Z_Stage", Bottom_z)
                            
                            for row in range(self.channel_tableWidget.rowCount()):
                                ch = self.channel_tableWidget.cellWidget(row, 0).currentText()
                                exp = self.channel_tableWidget.cellWidget(row, 1).value()

                                print(f'            Channel: {ch}, exp time: {exp}')
                                mmcore.setExposure(exp)
                                mmcore.setConfig("Channel", ch)
                                # mmcore.waitForDevice('')
                                mmcore.snapImage()
                                #put image in a stack
                                stack = self.pos_stack_array[position]
                                stack[t,z_position,row,:,:] = mmcore.getImage()

                            Bottom_z = Bottom_z + stepsize
                    
                    #save stack per position
                    #make a folder with the position name
                    if self.save_groupBox.isChecked():

                        position_format = format(len(self.pos_list), '04d')
                        t_format = format(t, '04d')
                        n_steps_format = format(n_steps, '04d')
                        nC_format = format(nC, '04d')

                        save_folder_name = f'{self.fname_lineEdit.text()}_Pos{position_format}_t{t_format}_z{n_steps_format}_c{nC_format}
                        pth = self.parent_path / f'{save_folder_name}.tif'
                        io.imsave(str(pth), stack, imagej=True, check_contrast=False)


                    if timeinterval_unit > 0 and t < timepoints - 1:
                        print(f"\nWaiting...Time interval = {timeinterval_unit/1000} seconds\n ")
                        #create a time indicator on the gui
                        # maybe use
                        # while True:
                        #   display the time changing

                    #save stack in a temp folder

                    mmcore.sleep(timeinterval_unit)


                



                end_acq_timr = time.perf_counter()


                summary = """
                _________________________________________
                Acq_time: {} Seconds
                _________________________________________
                """.format(round(end_acq_timr-start_acq_timr, 4))
                summary = dedent(summary)
                print(summary)


            else:
                print('Select at lest one channel.')
        else:
            print('Load a cfg file first.')



    # save_groupBox: QtW.QGroupBox
    # fname_lineEdit: QtW.QLineEdit
    # dir_lineEdit: QtW.QLineEdit
    # browse_save_Button: QtW.QPushButton

    # channel_groupBox: QtW.QGroupBox
    # channel_tableWidget: QtW.QTableWidget
    # add_ch_Button: QtW.QPushButton
    # clear_ch_Button: QtW.QPushButton
    # remove_ch_Button: QtW.QPushButton

    # time_groupBox: QtW.QGroupBox
    # frames_spinBox: QtW.QSpinBox
    # interval_spinBox: QtW.QSpinBox
    # time_comboBox: QtW.QComboBox

    # stack_groupBox: QtW.QGroupBox
    # step_spinBox: QtW.QSpinBox
    # step_size_doubleSpinBox: QtW.QDoubleSpinBox
    
    # stage_pos_groupBox: QtW.QGroupBox
    # stage_tableWidget: QtW.QTableWidget
    # add_pos_Button: QtW.QPushButton
    # clear_pos_Button: QtW.QPushButton
    # remove_pos_Button: QtW.QPushButton

    # acquisition_order_comboBox: QtW.QComboBox
    # run_Button: QtW.QPushButton











            # if self.save_groupBox.isChecked():
            #     name_list = []
            #     print('___')
            #     for name in os.listdir(self.parent_path):
            #         name_length = len(name)
            #         if name[-4:]=='.tif':
            #             name_1 = name[0:name_length-9]#name without .tif
            #             name_2 = name[-8:-4]#only numbers in the name
            #             if name_1==self.fname_rec_lineEdit.text():
            #                 name_list.append(name_2)   
            #     name_list.sort()
    
            #     i = format(0, '04d')
            #     for r in range(len(name_list)):
            #         if str(i) in name_list[r]:
            #             i = format(int(i)+1, '04d')
    
            #     pth = self.parent_path / f'{self.fname_rec_lineEdit.text()}_{i}.tif'
            #     io.imsave(str(pth), self.stack, imagej=True, check_contrast=False)
            #     print(pth)
            #     name_list.clear()
    
        # else:
        #    print('Load a configuration first!')
        #    #add dialog pop up window                                                            








    #in run button add 
    


    



    