import concurrent.futures
import os
import time
from pathlib import Path

import numpy as np
import pyfirmata2
from qtpy import QtCore
from qtpy import QtWidgets as QtW
from qtpy import uic
from qtpy.QtGui import QIcon
from skimage import io

from .qmmcore import QMMCore

ICONS = Path(__file__).parent / "icons"
UI_FILE = str(Path(__file__).parent / "_ui" / "optocamp_gui.ui")

mmcore = QMMCore()


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
    browse_rec_save_Button: QtW.QPushButton
    fname_rec_lineEdit: QtW.QLineEdit

    rec_Button: QtW.QPushButton

    def __init__(self, *args):
        super().__init__(*args)
        uic.loadUi(UI_FILE, self)

        self._viewer = None

        # button's icon
        self.rec_Button.setIcon(QIcon(str(ICONS / "play-button_1.svg")))
        self.rec_Button.setIconSize(QtCore.QSie(20, 20))

        # connect buttons
        self.detect_board_Button.clicked.connect(self.is_loaded)
        self.rec_Button.clicked.connect(self.start_recordings)
        self.browse_rec_save_Button.clicked.connect(self.save_recordongs)

        # connect spinBox
        self.delay_spinBox.valueChanged.connect(self.frame_values_changed)
        self.interval_spinBox.valueChanged.connect(self.frame_values_changed)
        self.Pulses_spinBox.valueChanged.connect(self.frame_values_changed)
        self.exp_spinBox_1.valueChanged.connect(self.frame_values_changed)

        self.led_start_pwr_spinBox.valueChanged.connect(self.led_values_changed)
        self.led_pwr_inc_spinBox.valueChanged.connect(self.led_values_changed)
        self.Pulses_spinBox.valueChanged.connect(self.led_values_changed)

        # connect toggle group box
        self.save_groupBox_rec.toggled.connect(self.toggle_rec_button)
        self.dir_rec_lineEdit.textChanged.connect(self.toggle_rec_button)
        self.fname_rec_lineEdit.textChanged.connect(self.toggle_rec_button)

    # def update_viewer(self, data):
    #     try:
    #         self.viewer.layers["preview"].data = data
    #     except KeyError:
    #         self.viewer.add_image(data, name="preview")

    def cfg_properties(self):
        self.oc_channel_comboBox.clear()
        # Get Channel List
        if "Channel" in mmcore.getAvailableConfigGroups():
            channel_list = list(mmcore.getAvailableConfigs("Channel"))
            self.oc_channel_comboBox.addItems(channel_list)
        else:
            print("Could not find 'Channel' in the ConfigGroups")

    def print_properties(self):
        # camera
        print(f"Camera: {mmcore.getCameraDevice()}")
        # binning
        binning = mmcore.getProperty(mmcore.getCameraDevice(), "Binning")
        print(f"Binning: {binning}")
        # bit depth
        bit = mmcore.getProperty(mmcore.getCameraDevice(), "PixelType")
        print(f"Bit Depth: {bit}")
        # stage position
        xpos = mmcore.getXPosition()
        ypos = mmcore.getYPosition()
        zpos = mmcore.getPosition("Z_Stage")
        print(f"Stage Positions:   x: {xpos}, y: {ypos}, z: {zpos}")

    def is_loaded(self):
        dev_loaded = list(mmcore.getLoadedDevices())
        if len(dev_loaded) > 1:
            self.detect_arduino()

    def detect_arduino(self):
        try:
            self.arduino_board_comboBox.clear()
            self.board = pyfirmata2.Arduino(pyfirmata2.Arduino.AUTODETECT)
            board_port = [str(self.board)]
            self.arduino_board_comboBox.addItems(board_port)
            it = pyfirmata2.util.Iterator(self.board)
            it.start()
            self.led = self.board.get_pin("d:3:p")  # set led pin of arduino

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

            # set info with default values
            self.frame_values_changed()
            self.led_values_changed()

        except KeyError:
            print("No Arduino Found")

    def frame_values_changed(self):
        self.n_frames = (
            self.delay_spinBox.value()
            + (self.interval_spinBox.value() * self.Pulses_spinBox.value())
        ) - 1
        self.tot_frames_label.setText(str(self.n_frames))
        total_rec_time = str(self.n_frames * self.exp_spinBox_1.value() / 1000)
        fps = str("%.3f" % (1000 / self.exp_spinBox_1.value()))
        self.rec_time_label.setText(
            f"{total_rec_time} seconds @ {fps} frames per second."
        )
        # self.rec_time_label.setText(str((self.n_frames*self.exp_spinBox_1.value()/1000)))
        frames_stim = []
        fr = self.delay_spinBox.value()
        for i in range(self.Pulses_spinBox.value()):
            frames_stim.append(fr)
            fr = fr + self.interval_spinBox.value()
        self.frame_w_pulses_label.setText(str(frames_stim))

    def led_values_changed(self):
        led_power_used = []
        pwr = self.led_start_pwr_spinBox.value()
        for _ in range(self.Pulses_spinBox.value()):
            led_power_used.append(pwr)
            pwr = pwr + self.led_pwr_inc_spinBox.value()

        self.led_pwrs_label.setText(str(led_power_used))

        power_max = self.led_start_pwr_spinBox.value() + (
            self.led_pwr_inc_spinBox.value() * (self.Pulses_spinBox.value() - 1)
        )
        self.led_max_pwr_label.setText(str(power_max))

        if power_max > 100:
            self.rec_Button.setEnabled(False)
            self.led_max_pwr_label.setText("LED max power exceded!!!")
        else:
            self.rec_Button.setEnabled(True)
            self.led_max_pwr_label.setText(str(power_max))

        led_power_used.clear()

    def save_recordongs(self):
        # set the directory
        self.dir = QtW.QFileDialog(self)
        self.dir.setFileMode(QtW.QFileDialog.DirectoryOnly)
        self.save_dir = QtW.QFileDialog.getExistingDirectory(self.dir)
        self.dir_rec_lineEdit.setText(self.save_dir)
        self.parent_path = Path(self.save_dir)

    def snap_optocamp(self, exp_t, i):
        time.sleep(0.001)
        mmcore.setExposure(exp_t)
        # print('  snap')
        s_cam = time.perf_counter()
        mmcore.snapImage()
        e_cam = time.perf_counter()
        print(f"   cam on for {round(e_cam - s_cam, 4)} second(s)")
        self.stack[i - 1, :, :] = mmcore.getImage()

        # self.update_viewer(self.stack)#?????

    def led_on(self, power, on_for):
        self.led.write(power)
        s = time.perf_counter()
        time.sleep(on_for)
        self.led.write(0.0)
        e = time.perf_counter()
        print(f"    led on for {round(e-s, 4)} second(s)")
        # print(f'  led_power = {power}')

    def toggle_rec_button(self):
        if self.save_groupBox_rec.isChecked():
            if (
                self.dir_rec_lineEdit.text() == ""
                or self.fname_rec_lineEdit.text() == ""
            ):
                self.rec_Button.setEnabled(False)
            else:
                self.rec_Button.setEnabled(True)

    def start_recordings(self):
        self.print_properties()

        # print(f'get camera ROI: {mmcore.getROI(mmcore.getCameraDevice())}')
        width = mmcore.getROI(mmcore.getCameraDevice())[2]
        height = mmcore.getROI(mmcore.getCameraDevice())[3]
        self.stack = np.empty((self.n_frames, height, width), dtype=np.uint16)
        # print(self.stack.shape)

        time_stamp = []
        stim_frame = self.delay_spinBox.value()
        start_led_power = self.led_start_pwr_spinBox.value()
        # print(f'start led power (%): {start_led_power}')
        # print(f'start led power (float): {float(start_led_power/100)}')

        mmcore.setConfig("Channel", self.oc_channel_comboBox.currentText())

        for i in range(1, (self.n_frames + 1)):

            # print(f'frame: {i}')

            if i == stim_frame:

                tm = time.time()
                time_stamp.append(tm)

                start = time.perf_counter()

                ########
                # self.snap_optocamp(int(self.exp_spinBox_1.value()))
                # self.led_on(
                #     (start_led_power / 100), (int(self.exp_spinBox_1.value()) / 1000)
                # )
                # ########

                # ########
                # t_snap = threading.Thread(
                #     target=self.snap_optocamp, args=[int(self.exp_spinBox_1.value())]
                # )
                # t_led = threading.Thread(
                #     target=self.led_on,
                #     args=[
                #         (start_led_power / 100),
                #         (int(self.exp_spinBox_1.value()) / 1000),
                #     ],
                # )

                # t_snap.start()
                # t_led.start()

                # t_snap.join()
                # t_led.join()
                ########

                #######
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    executor.submit(
                        self.snap_optocamp, int(self.exp_spinBox_1.value()), i
                    )
                    executor.submit(
                        self.led_on,
                        float(start_led_power / 100),
                        (int(self.exp_spinBox_1.value()) / 1000),
                    )
                #######

                finish = time.perf_counter()
                print(f"Finished in {round(finish-start, 4)} second(s)")

                stim_frame = stim_frame + self.interval_spinBox.value()
                start_led_power = start_led_power + self.led_pwr_inc_spinBox.value()

            else:
                self.snap_optocamp(int(self.exp_spinBox_1.value()), i)
                tm = time.time()
                time_stamp.append(tm)

        if self.save_groupBox_rec.isChecked():
            name_list = []
            print("___")
            for name in os.listdir(self.parent_path):
                name_length = len(name)
                if name[-4:] == ".tif":
                    name_1 = name[0 : name_length - 9]  # name without .tif
                    name_2 = name[-8:-4]  # only numbers in the name
                    if name_1 == self.fname_rec_lineEdit.text():
                        name_list.append(name_2)
            name_list.sort()

            i = format(0, "04d")
            for r in range(len(name_list)):
                if str(i) in name_list[r]:
                    i = format(int(i) + 1, "04d")

            pth = self.parent_path / f"{self.fname_rec_lineEdit.text()}_{i}.tif"
            io.imsave(str(pth), self.stack, imagej=True, check_contrast=False)
            name_list.clear()

        print("***END***")

        # self.board.exit()

        # print('SUMMARY \n**********')
        # print(f'Recordings lenght: {n_frames} frames')
        # print(f'Number of Stimulations: {n_stimulations}')
        # print(f'Frames when Stimulation occurred: {frames_stim}')
        # print(f'Led Power: {led_power_used} percent')
        # print('**********')

        # gap_list = []
        # for i in range (len(time_stamp)):
        #    val1 = time_stamp[i]
        #    if i<len(time_stamp)-1:
        #        val2 = time_stamp[i+1]
        #    else:
        #        break
        #    gap = (val2-val1)*1000
        #    gap_list.append(gap)
        # print(f'Timestamp: {gap_list[0]}, {gap_list[1]}, {gap_list[len(gap_list)-1]}')


# self.objective_comboBox.currentIndexChanged.connect(self.change_objective)
