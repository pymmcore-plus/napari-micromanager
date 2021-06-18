from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
import warnings

from qtpy import QtWidgets as QtW
from qtpy import uic
from useq import MDASequence

import numpy as np
from skimage.transform import resize

if TYPE_CHECKING:
    from pymmcore_remote import RemoteMMCore

UI_FILE = str(Path(__file__).parent / "_ui" / "explore_sample.ui")


class ExploreSample(QtW.QWidget):
    # The UI_FILE above contains these objects:
    scan_size_label: QtW.QLabel
    scan_size_spinBox_r: QtW.QSpinBox
    scan_size_spinBox_c: QtW.QSpinBox
    scan_channel_comboBox: QtW.QComboBox
    scan_exp_spinBox: QtW.QSpinBox
    start_scan_Button: QtW.QPushButton
    stop_scan_Button: QtW.QPushButton
    move_to_Button: QtW.QPushButton
    x_lineEdit: QtW.QLineEdit
    y_lineEdit: QtW.QLineEdit
    ovelap_spinBox: QtW.QSpinBox
    save_explorer_groupBox: QtW.QGroupBox
    dir_explorer_lineEdit: QtW.QLineEdit
    fname_explorer_lineEdit: QtW.QLineEdit
    browse_save_explorer_Button: QtW.QPushButton



    def __init__(self, mmcore, parent=None):
            self._mmc = mmcore
            super().__init__(parent)  
            uic.loadUi(UI_FILE, self)

            self.start_scan_Button.clicked.connect(self.start_scan)
            self.move_to_Button.clicked.connect(self.move_to)
            self.browse_save_explorer_Button.clicked.connect(self.set_explorer_dir)
    
    def enable_explorer_groupbox(self):
        self.scan_size_spinBox_r.setEnabled(True)
        self.scan_size_spinBox_c.setEnabled(True)
        self.ovelap_spinBox.setEnabled(True)
        self.scan_channel_comboBox.setEnabled(True)
        self.scan_exp_spinBox.setEnabled(True)
        self.move_to_Button.setEnabled(True)
        self.start_scan_Button.setEnabled(True)
        self.save_explorer_groupBox.setEnabled(True)

    def disable_explorer_groupbox(self):
        self.scan_size_spinBox_r.setEnabled(False)
        self.scan_size_spinBox_c.setEnabled(False)
        self.ovelap_spinBox.setEnabled(False)
        self.scan_channel_comboBox.setEnabled(False)
        self.scan_exp_spinBox.setEnabled(False)
        self.move_to_Button.setEnabled(False)
        self.start_scan_Button.setEnabled(False)
        self.save_explorer_groupBox.setEnabled(False)

    def _get_state_dict(self) -> dict:
        state = {
            "axis_order": 'tpzc',
            "channels": [],
            "stage_positions": [],
            "z_plan": None,
            "time_plan": None,
            "extras": 'sample_explorer'
        }

        # channel settings
        state["channels"] = [
            {
                "config": self.scan_channel_comboBox.currentText(),
                "group": self._mmc.getChannelGroup() or "Channel",
                "exposure": self.scan_exp_spinBox.value(),
            }
        ]

        # position settings
        postions_grid = self.set_grid()

        for r in range(len(postions_grid)):

            state["stage_positions"].append(
                {
                    "x": float(postions_grid[r][0]),
                    "y": float(postions_grid[r][1]),
                    "z": float(postions_grid[r][2]),
                }
            )

        return state

    
    def set_grid(self):

        self.scan_size_r = self.scan_size_spinBox_r.value()
        self.scan_size_c = self.scan_size_spinBox_c.value()

        #get current position
        x_curr_pos_explorer = float(self._mmc.getXPosition())
        y_curr_pos_explorer = float(self._mmc.getYPosition())
        z_curr_pos_explorer = float(self._mmc.getZPosition())

        #calculate initial scan position
        width = self._mmc.getROI(self._mmc.getCameraDevice())[2]  # maybe they are inverted
        height = self._mmc.getROI(self._mmc.getCameraDevice())[3]  # maybe they are inverted

        overlap_percentage = self.ovelap_spinBox.value()
        overlap_px_w = width - (width * overlap_percentage)/100
        overlap_px_h = height - (height * overlap_percentage)/100

        if self.scan_size_r == 1 and self.scan_size_c > 1:
            move_x = (((width / 2) * (self.scan_size_c - 1)) - overlap_px_w) * self._mmc.getPixelSizeUm()
            move_y = 0

        elif self.scan_size_r > 1 and self.scan_size_c == 1:
            move_x = 0
            move_y = (((height / 2) * (self.scan_size_r - 1)) - overlap_px_h)  * self._mmc.getPixelSizeUm()

        else:
            move_x = (((width / 2) * (self.scan_size_c - 1)) - overlap_px_w) * self._mmc.getPixelSizeUm()
            move_y = (((height / 2) * (self.scan_size_r - 1)) - overlap_px_h)  * self._mmc.getPixelSizeUm()

        x_pos_explorer = x_curr_pos_explorer - move_x
        y_pos_explorer = y_curr_pos_explorer + move_y


        #calculate position increments depending on pixle size
        if overlap_percentage > 0:
            increment_x = overlap_px_w * self._mmc.getPixelSizeUm()
            increment_y = overlap_px_h * self._mmc.getPixelSizeUm()
        else:
            increment_x = width * self._mmc.getPixelSizeUm()
            increment_y = height * self._mmc.getPixelSizeUm()

        list_pos_order  = []

        #create the xyz position matrix
        for r in range(self.scan_size_r):
            if r == 0 or (r % 2) == 0:
                for c in range(self.scan_size_c):# for even rows
                    if r > 0 and c == 0:
                        y_pos_explorer = y_pos_explorer - increment_y
                    list_pos_order.append([x_pos_explorer,y_pos_explorer,z_curr_pos_explorer])
                    if c < self.scan_size_c - 1:
                        x_pos_explorer = x_pos_explorer + increment_x
            else:# for odd rows
                col = self.scan_size_c - 1
                for c in range(self.scan_size_c):
                    if c == 0:
                        y_pos_explorer = y_pos_explorer - increment_y
                    list_pos_order.append([x_pos_explorer,y_pos_explorer,z_curr_pos_explorer])
                    if col > 0:
                        col = col - 1
                        x_pos_explorer = x_pos_explorer - increment_x

        return list_pos_order
    
    def set_explorer_dir(self):
        # set the directory
        self.dir = QtW.QFileDialog(self)
        self.dir.setFileMode(QtW.QFileDialog.DirectoryOnly)
        self.save_dir = QtW.QFileDialog.getExistingDirectory(self.dir)
        self.dir_explorer_lineEdit.setText(self.save_dir)
        self.parent_path = Path(self.save_dir)
        
    def start_scan(self):

        if not self._mmc.getPixelSizeUm() > 0:
            raise ValueError ('PIXEL SIZE NOT SET.')
        
        if self.save_explorer_groupBox.isChecked() and \
            (self.fname_explorer_lineEdit.text() == '' or \
                (self.dir_explorer_lineEdit.text() == '' or \
                    not Path.is_dir(Path(self.dir_explorer_lineEdit.text()))
                    )):
                        raise ValueError ('select a filename and a valid directory.')

        self.explore_sample = MDASequence(**self._get_state_dict())
        self._mmc.run_mda(self.explore_sample)  # run the MDA experiment asynchronously
        return

    def move_to(self):

        move_to_x = self.x_lineEdit.text()
        move_to_y = self.y_lineEdit.text()

        if move_to_x == "None" and move_to_y == "None":
            warnings.warn('PIXEL SIZE NOT SET.')
        else:
            move_to_x = float(move_to_x)
            move_to_y = float(move_to_y)
            self._mmc.setXYPosition(float(move_to_x), float(move_to_y))


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication

    app = QApplication([])
    window = ExploreSample()
    window.show()
    app.exec_()

