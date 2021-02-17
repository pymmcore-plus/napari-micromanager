import os
import sys
from pathlib import Path
import numpy as np
from PyQt5 import QtWidgets as QtW
from qtpy import uic
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5 import QtCore
from skimage import io
from skimage.transform import resize
import time

from .mmcore_pymmcore import MMCore

UI_FILE = str(Path(__file__).parent / "explore_sample.ui")

mmcore = MMCore()

class ExploreSample(QtW.QWidget):
    # The UI_FILE above contains these objects:
    scan_size_label: QtW.QLabel
    scan_size_spinBox_x: QtW.QSpinBox
    scan_size_spinBox_y: QtW.QSpinBox
    scan_channel_comboBox: QtW.QComboBox
    scan_exp_spinBox: QtW.QSpinBox
    start_scan_Button: QtW.QPushButton
    stop_scan_Button: QtW.QPushButton
    progressBar: QtW.QProgressBar
    move_to_Button: QtW.QPushButton
    x_lineEdit: QtW.QLineEdit
    y_lineEdit: QtW.QLineEdit

    #________________________________________________________________________
    new_frame = Signal(str, np.ndarray)
    send_explorer_info = Signal(int, int)
    delete_snaps = Signal(str)
    delete_previous_scan = Signal(str)
    #________________________________________________________________________


    def __init__(self, *args):
        super().__init__(*args)
        uic.loadUi(UI_FILE, self)

        self.scan_position_list = []
        self.stitched_image_array_list = []
        self.x_lineEdit.setText('None')
        self.y_lineEdit.setText('None')
        # self.scan_size = 'None'
        self.scan_size_x = 'None'
        self.scan_size_y = 'None'

       
        self.start_scan_Button.clicked.connect(self.start_scan)
        self.stop_scan_Button.clicked.connect(self.stop_scan)
        self.move_to_Button.clicked.connect(self.move_to)

    def stop_scan(self):
        pass

    def start_scan(self):

        # name = f'stitched_{self.scan_size}x{self.scan_size}'
        name = f'stitched_{self.scan_size_x}x{self.scan_size_y}'
        self.delete_previous_scan.emit(name)#emot signal to MainWindow

        self.x_lineEdit.setText('None')
        self.y_lineEdit.setText('None')

        # self.scan_size = self.scan_size_spinBox.value()
        self.scan_size_x = self.scan_size_spinBox_x.value()#self.scan_size_spinBox_x
        self.scan_size_y = self.scan_size_spinBox_y.value()#self.scan_size_spinBox_y

        self.scan_position_list.clear()
        self.stitched_image_array_list.clear()
        
        self.scaling_factor = 3

        # self.total_size = self.scan_size*self.scan_size
        self.total_size = self.scan_size_x*self.scan_size_y

        #create positions storage arrays
        # self.array_pos_x = np.empty((self.scan_size,self.scan_size))
        # self.array_pos_y  = np.empty((self.scan_size,self.scan_size))
        # self.array_pos_z  = np.empty((self.scan_size,self.scan_size))
        self.array_pos_x = np.empty((self.scan_size_x,self.scan_size_y))
        self.array_pos_y  = np.empty((self.scan_size_x,self.scan_size_y))
        self.array_pos_z  = np.empty((self.scan_size_x,self.scan_size_y))
        

        #for progress bar
        prigress_values = np.linspace(1, 90, self.total_size)
        prigress_values = np.round(prigress_values,0)
        prigress_values = prigress_values.astype(int)

        #set acquisition parameters
        mmcore.setExposure(int(self.scan_exp_spinBox.value()))
        mmcore.setConfig("Channel", self.scan_channel_comboBox.currentText())
        
        #get current position
        x_curr_pos_explorer = int(mmcore.getXPosition())
        y_curr_pos_explorer = int(mmcore.getYPosition())
        z_curr_pos_explorer = int(mmcore.getPosition("Z_Stage"))
        # print(f'curr_pos:{x_curr_pos_explorer},{y_curr_pos_explorer},{z_curr_pos_explorer}')

        #calculate initial scan position
        self.width = mmcore.getROI(mmcore.getCameraDevice())[2]#maybe they are inverted
        self.height = mmcore.getROI(mmcore.getCameraDevice())[3]#maybe they are inverted
        # move_x = (self.width/2)*(self.scan_size-1)*mmcore.getPixelSizeUm()
        # move_y = (self.height/2)*(self.scan_size-1)*mmcore.getPixelSizeUm()
        move_x = (self.width/2)*(self.scan_size_x-1)*mmcore.getPixelSizeUm()
        move_y = (self.height/2)*(self.scan_size_y-1)*mmcore.getPixelSizeUm()


        x_pos_explorer = x_curr_pos_explorer - move_x
        y_pos_explorer = y_curr_pos_explorer + move_y
        # print(f'start pos: {x_pos_explorer},{y_pos_explorer}')

        #calculate position increments depending on pixle size
        increment_x = self.width * mmcore.getPixelSizeUm()
        increment_y = self.height * mmcore.getPixelSizeUm()
        # print(f'increments: {increment_x},{increment_y}')

        #create the xyz position matrix 
        # for r in range(self.scan_size):
        for r in range(self.scan_size_x):
            if r == 0 or (r % 2) == 0:
                # for c in range(self.scan_size):#for even rows
                for c in range(self.scan_size_y):
                    if r>0 and c == 0:
                        y_pos_explorer = y_pos_explorer - increment_y
                    self.array_pos_x[r][c] = x_pos_explorer
                    self.array_pos_y[r][c] = y_pos_explorer
                    self.array_pos_z[r][c] = z_curr_pos_explorer
                    # if c < self.scan_size-1:
                    if c < self.scan_size_y-1:
                        x_pos_explorer = x_pos_explorer + increment_x   
            else:#for odd rows
                # col = self.scan_size-1
                col = self.scan_size_y-1
                # for c in range(self.scan_size):
                for c in range(self.scan_size_y):
                    if c == 0:
                        y_pos_explorer = y_pos_explorer - increment_y
                    self.array_pos_x[r][col] = x_pos_explorer
                    self.array_pos_y[r][col] = y_pos_explorer
                    self.array_pos_z[r][col] = z_curr_pos_explorer
                    if col>0:
                        col = col - 1
                        x_pos_explorer = x_pos_explorer - increment_x  
        
        # print(f'\n{self.array_pos_x}\n\n{self.array_pos_y}\n\n{self.array_pos_z}\n')

        #move to the correct position and acquire an image
        progress = 0
        # for row in range(self.scan_size):
        for row in range(self.scan_size_x):
            if row == 0 or (row % 2) == 0:#for even rows
                # print(f'row {row} is even')
                # for s in range(self.scan_size):
                for s in range(self.scan_size_y):      
                    # move to position
                    vx = self.array_pos_x[row][s]
                    vy = self.array_pos_y[row][s]
                    vz = self.array_pos_z[row][s]
                    # print(f'even row: {vx},{vy},{vz}')
                    mmcore.setXYPosition(vx,vy)
                    mmcore.setPosition("Z_Stage", vz)
                    # print(mmcore.getXPosition(),mmcore.getYPosition(),mmcore.getPosition("Z_Stage"))

                    #snap image
                    mmcore.snapImage() 
                    snap = mmcore.getImage()
                    # print(f'    temp_snap_{row}_{s}')

                    #scale down image
                    snap_scaled = resize(snap, (round(self.height/self.scaling_factor), round(self.width/self.scaling_factor)))
                    self.new_frame.emit(f'temp_snap', snap_scaled)

                    #concatenate image in a row (to the right)
                    if s == 0:
                        stitched_image_array = snap_scaled
                    else:
                        stitched_image_array = np.concatenate((stitched_image_array, snap_scaled), axis = 1)
    
                    # print(f'        progress = {progress}, progressBar = {prigress_values[progress]}')
                    self.progressBar.setValue(prigress_values[progress])
                    progress += 1

                    time.sleep(0.1)
                    
                #append array in a list
                self.stitched_image_array_list.append(stitched_image_array)
                # print(f'            stitched_image_array.shape = {stitched_image_array.shape}')

            else:#for odd rows
                # print(f'row {row} is odd')
                # col = self.scan_size-1
                col = self.scan_size_y-1
                # for s in range(self.scan_size):
                for s in range(self.scan_size_y):
                    # print(f'col = {col}')

                    # move to position
                    vx = self.array_pos_x[row][col]
                    vy = self.array_pos_y[row][col]
                    vz = self.array_pos_z[row][col]
                    # print(f'odd row: {vx},{vy},{vz}')
                    mmcore.setXYPosition(vx,vy)
                    mmcore.setPosition("Z_Stage", vz)
                    # print(mmcore.getXPosition(),mmcore.getYPosition(),mmcore.getPosition("Z_Stage"))

                    #snap image
                    mmcore.snapImage() 
                    snap = mmcore.getImage()
                    # print(f'    temp_snap_{row}_{s}')

                    #scale down image
                    snap_scaled = resize(snap, (round(self.height/self.scaling_factor), round(self.width/self.scaling_factor)))
                    self.new_frame.emit(f'temp_snap', snap_scaled)

                    #concatenate image in a row (to the left)
                    if s == 0:
                        stitched_image_array = snap_scaled
                    else:
                        stitched_image_array = np.concatenate((snap_scaled, stitched_image_array), axis = 1)
                    
                    # print(f'        progress = {progress}, progressBar = {prigress_values[progress]}')
                    self.progressBar.setValue(prigress_values[progress])
                    progress += 1
                    if col>0:
                        col = col - 1

                    time.sleep(0.1)

                #append array in a list
                self.stitched_image_array_list.append(stitched_image_array)
                # print(f'            stitched_image_array.shape = {stitched_image_array.shape}')

        #stitch all rows
        stitched_image_final = self.stitched_image_array_list[0] 
        for row in range(1,len(self.stitched_image_array_list)):
            st = self.stitched_image_array_list[row]
            stitched_image_final = np.concatenate((stitched_image_final, st), axis = 0)
        # print(f'stitched_image_final.shape = {stitched_image_final.shape}')
        # self.new_frame.emit(f'stitched_{self.scan_size}x{self.scan_size}', stitched_image_final)
        self.new_frame.emit(f'stitched_{self.scan_size_x}x{self.scan_size_y}', stitched_image_final)
        self.progressBar.setValue(100)
        self.shape_stitched_x = stitched_image_final.shape[1]
        self.shape_stitched_y = stitched_image_final.shape[0]

        self.send_explorer_info.emit(self.shape_stitched_x, self.shape_stitched_y)#emit signal to MainWindow
        self.delete_snaps.emit('temp_snap')#emit signal to MainWindow

    def move_to(self):
        
        string_coord_x = self.x_lineEdit.text()
        string_coord_y = self.y_lineEdit.text()

        if not string_coord_x == 'None' and not string_coord_y == 'None':

            coord_x = float(string_coord_x)
            coord_y = float(string_coord_y)
            # print(f'COORDS: {coord_x},{coord_y}')

            # x_snap = self.shape_stitched_x/self.scan_size
            # y_snap = self.shape_stitched_y/self.scan_size
            x_snap = self.shape_stitched_x/self.scan_size_x
            y_snap = self.shape_stitched_y/self.scan_size_y
            # print(x_snap, y_snap)

            x_snap_increment = x_snap
            y_snap_increment = y_snap

            done = False
            col = 0
            for _ in range(self.total_size):

                if done:
                    break

                if coord_x <= x_snap:
                    # for row in range(self.scan_size):
                    for row in range(self.scan_size_x):
                        if coord_y <= y_snap:
                            # print(f'coord_x = {coord_x}, coord_y = {coord_y}')
                            # print(f'row = {row}, col = {col}')
                            x_scan_pos = self.array_pos_x[row][col]
                            y_scan_pos = self.array_pos_y[row][col]
                            z_scan_pos = self.array_pos_z[row][col]
                            # print(f'moving to x: {x_scan_pos}')
                            # print(f'moving to y: {y_scan_pos}')
                            # print(f'moving to z: {z_scan_pos}')
                            #set position
                            mmcore.setXYPosition(x_scan_pos,y_scan_pos)
                            mmcore.setPosition("Z_Stage", z_scan_pos)

                            #snap image at position
                            mmcore.setExposure(int(self.scan_exp_spinBox.value()))
                            mmcore.setConfig("Channel", self.scan_channel_comboBox.currentText())
                            mmcore.snapImage()
                            image = mmcore.getImage()
                            self.new_frame.emit('preview', image)
                            done = True
                            break

                        else:
                            y_snap = y_snap + y_snap_increment
                else:
                    x_snap = x_snap + x_snap_increment
                    col += 1






     









