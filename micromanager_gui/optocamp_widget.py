import os
import sys
from pathlib import Path
import numpy as np
from PyQt5 import QtWidgets as QtW
from qtpy import uic
import time
from qtpy.QtWidgets import QFileDialog

from pyfirmata2 import Arduino, util
import concurrent.futures
import threading#

from mmcore_pymmcore import MMCore

import napari


UI_FILE = str(Path(__file__).parent / "optocamp_gui.ui")

mmcore = MMCore()

class OptocampWidget(QtW.QWidget):
    # The UI_FILE above contains these objects:
    arduino_groupBox: QtW.QGroupBox
    arduino_board_comboBox: QtW.QComboBox
    detect_board_Button: QtW.QPushButton

    exp_groupBox_1: QtW.QGroupBox
    exp_spinBox_1: QtW.QSpinBox

    oc_channel_groupBox: QtW.QGroupBox
    oc_channel_comboBox: QtW.QComboBox

    frames_groupBox: QtW.QGroupBox
    delay_spinBox: QtW.QSpinBox
    interval_spinBox: QtW.QSpinBox
    Pulses_spinBox: QtW.QSpinBox
    tot_frames_label: QtW.QLabel
    frame_w_pulses_label: QtW.QLabel
    rec_time_label: QtW.QLabel

    led_groupBox: QtW.QGroupBox
    led_start_pwr_spinBox: QtW.QSpinBox
    led_pwr_inc_spinBox: QtW.QSpinBox
    led_pwrs_label: QtW.QLabel
    led_max_pwr_label: QtW.QLabel

    save_groupBox_rec: QtW.QGroupBox
    dir_rec_lineEdit: QtW.QLineEdit
    browse_rec_save_Button:QtW.QPushButton
    fname_rec_lineEdit: QtW.QLineEdit

    rec_Button: QtW.QPushButton

    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(UI_FILE, self)

        #connect buttons
        self.detect_board_Button.clicked.connect(self.is_loaded)
        self.rec_Button.clicked.connect(self.start_recordings)

        #connect spinBox
        self.delay_spinBox.valueChanged.connect(self.frame_values_changed)
        self.interval_spinBox.valueChanged.connect(self.frame_values_changed)
        self.Pulses_spinBox.valueChanged.connect(self.frame_values_changed)
        self.exp_spinBox_1.valueChanged.connect(self.frame_values_changed)

        self.led_start_pwr_spinBox.valueChanged.connect(self.led_values_changed)
        self.led_pwr_inc_spinBox.valueChanged.connect(self.led_values_changed)
        self.Pulses_spinBox.valueChanged.connect(self.led_values_changed)

    @property
    def viewer(self):
        # lazy creation
        par = self.parent()
        print(par)
        print(par.__class__.__module__)
        if "napari" in par.__class__.__module__:
            return par.qt_viewer.viewer
        if not self._viewer:
             self._viewer = napari.Viewer()
        try:
            self._viewer.show()
        except RuntimeError:
            self._viewer = napari.Viewer()
        return self._viewer

    # def update_viewer(self, data):
    #     try:
    #         self.viewer.layers["preview"].data = data
    #     except KeyError:
    #         self.viewer.add_image(data, name="preview")

    def cfg_properties(self):
        self.oc_channel_comboBox.clear()
        #Get Channel List
        if "Channel" in mmcore.getAvailableConfigGroups():
            channel_list = list(mmcore.getAvailableConfigs("Channel"))
            self.oc_channel_comboBox.addItems(channel_list)
        else:
            print("Could not find 'Channel' in the ConfigGroups")
        
    def print_properties(self):
        #binning
        binning = mmcore.getProperty(mmcore.getCameraDevice(), "Binning")
        print(f'Binning: {binning}')
        #bit depth
        bit = mmcore.getProperty(mmcore.getCameraDevice(), "PixelType")
        print(f'Bit Depth: {bit}')
        #stage position
        xpos = mmcore.getXPosition()
        ypos = mmcore.getYPosition()
        zpos = mmcore.getPosition("Z_Stage")
        print(f'Stage Positions:   x: {xpos}, y: {ypos}, z: {zpos}')

    def is_loaded(self):
        dev_loaded = list(mmcore.getLoadedDevices())
        if len(dev_loaded) > 1:
            self.detect_arduino()
    
    def detect_arduino(self):
        try:
            self.arduino_board_comboBox.clear()
            self.board = Arduino(Arduino.AUTODETECT)
            board_port = [str(self.board)]
            self.arduino_board_comboBox.addItems(board_port)
            it = util.Iterator(self.board)
            it.start()
            self.led = self.board.get_pin('d:3:p')#set led pin of arduino

            self.oc_channel_comboBox.setEnabled(True)
            self.cfg_properties()
            self.exp_groupBox_1.setEnabled(True)
            self.exp_spinBox_1.setEnabled(True)
            self.frames_groupBox.setEnabled(True)
            self.delay_spinBox.setEnabled(True)
            self.interval_spinBox.setEnabled(True)
            self.Pulses_spinBox.setEnabled(True)

            self.led_groupBox.setEnabled(True)
            self.led_start_pwr_spinBox.setEnabled(True)
            self.led_pwr_inc_spinBox.setEnabled(True)
            self.save_groupBox_rec.setEnabled(True)
            self.rec_Button.setEnabled(True)

            #set info with default values
            self.frame_values_changed()
            self.led_values_changed()

        except KeyError:
            print('No Arduino Found')

    def frame_values_changed(self):
        self.n_frames = (self.delay_spinBox.value() + (self.interval_spinBox.value()*self.Pulses_spinBox.value()))-1
        self.tot_frames_label.setText(str(self.n_frames))
        self.rec_time_label.setText(str((self.n_frames*self.exp_spinBox_1.value()/1000)))
        frames_stim = []
        fr = self.delay_spinBox.value()
        for i in range (self.Pulses_spinBox.value()):
            frames_stim.append(fr)
            fr = fr + self.interval_spinBox.value()
        self.frame_w_pulses_label.setText(str(frames_stim))

    def led_values_changed(self):
        led_power_used = []
        pwr = self.led_start_pwr_spinBox.value()
        for _ in range (self.Pulses_spinBox.value()):
            led_power_used.append(pwr)
            pwr = pwr + self.led_pwr_inc_spinBox.value()
        
        self.led_pwrs_label.setText(str(led_power_used))

        power_max = (self.led_start_pwr_spinBox.value()+(self.led_pwr_inc_spinBox.value()*(self.Pulses_spinBox.value()-1)))
        self.led_max_pwr_label.setText(str(power_max))
        
        if power_max > 100:
            self.rec_Button.setEnabled(False)
            self.led_max_pwr_label.setText('LED max power exceded!!!')
        else:
            self.rec_Button.setEnabled(True)
            self.led_max_pwr_label.setText(str(power_max))

        led_power_used.clear()

    def save_recordongs(self):
        save_groupBox_rec: QtW.QGroupBox
        dir_rec_lineEdit: QtW.QLineEdit
        browse_rec_save_Button: QtW.QPushButton
        fname_rec_lineEdit: QtW.QLineEdit

    def snap_optocamp(self, exp_t):
        time.sleep(0.001)
        mmcore.setExposure(exp_t)
        #print('  snap')
        s_cam = time.perf_counter()
        mmcore.snapImage()
        e_cam = time.perf_counter()
        print(f'   cam on for {round(e_cam - s_cam, 4)} second(s)')################################################
        #self.update_viewer(mmcore.getImage())#?????

    def led_on(self, power, on_for):
        self.led.write(power)
        s = time.perf_counter()
        time.sleep(on_for)
        self.led.write(0.0)
        e = time.perf_counter()
        print(f'    led on for {round(e-s, 4)} second(s)')################################################
        #print(f'  led_power = {power}')
        
    def start_recordings(self):
        self.print_properties()

        time_stamp = []
        stim_frame = self.delay_spinBox.value()
        start_led_power = self.led_start_pwr_spinBox.value()
        #print(f'start led power (%): {start_led_power}')
        #print(f'start led power (float): {float(start_led_power/100)}')

        for i in range (1,(self.n_frames+1)):
            
            #print(f'frame: {i}')

            mmcore.setConfig("Channel", self.oc_channel_comboBox.currentText())
     
            if i == stim_frame:

                tm = time.time()
                time_stamp.append(tm)

                start = time.perf_counter()

                ########
                # self.snap_optocamp(int(self.exp_spinBox_1.value()))
                # self.led_on((start_led_power/100), (int(self.exp_spinBox_1.value())/1000))
                # ########

                # ########
                # t_snap = threading.Thread(target=self.snap_optocamp, args = [int(self.exp_spinBox_1.value())])
                # t_led = threading.Thread(target=self.led_on, args = [(start_led_power/100),(int(self.exp_spinBox_1.value())/1000)])
                
                # t_snap.start()
                # t_led.start()

                # t_snap.join()
                # t_led.join()
                ########

                #######
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    t1 = executor.submit(self.snap_optocamp, int(self.exp_spinBox_1.value()))
                    t2 = executor.submit(self.led_on, float(start_led_power/100), (int(self.exp_spinBox_1.value())/1000))
                #######

                finish = time.perf_counter()
                print(f'Finished in {round(finish-start, 4)} second(s)')

                stim_frame = stim_frame + self.interval_spinBox.value()
                start_led_power = start_led_power + self.led_pwr_inc_spinBox.value()
                #print(f'start_led_power: {start_led_power}, interval: {self.led_pwr_inc_spinBox.value()}')
                #print(f'new_power: {start_led_power}')
            
            else:
                self.snap_optocamp(int(self.exp_spinBox_1.value()))
                tm = time.time()
                time_stamp.append(tm)
                
        print('***END***')       
    
        #self.board.exit()

        #print('SUMMARY \n**********')
        #print(f'Recordings lenght: {n_frames} frames')
        #print(f'Number of Stimulations: {n_stimulations}')
        #print(f'Frames when Stimulation occurred: {frames_stim}')
        #print(f'Led Power: {led_power_used} percent')
        #print('**********')

        #gap_list = []
        #for i in range (len(time_stamp)):
        #    val1 = time_stamp[i]
        #    if i<len(time_stamp)-1:
        #        val2 = time_stamp[i+1]
        #    else:
        #        break
        #    gap = (val2-val1)*1000
        #    gap_list.append(gap)
        #print(f'Timestamp: {gap_list[0]}, {gap_list[1]}, {gap_list[len(gap_list)-1]}')










#self.objective_comboBox.currentIndexChanged.connect(self.change_objective)


        