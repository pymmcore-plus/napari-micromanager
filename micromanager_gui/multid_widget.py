from pathlib import Path

import numpy as np
from qtpy import QtWidgets as QtW
from qtpy import uic
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QIcon

from ._mda_sequence import MDASequence
from .qmmcore import QMMCore

ICONS = Path(__file__).parent / "icons"
UI_FILE = str(Path(__file__).parent / "_ui" / "multid_gui.ui")

mmcore = QMMCore()


class MultiDWidget(QtW.QWidget):
    # The UI_FILE above contains these objects:
    save_groupBox: QtW.QGroupBox
    fname_lineEdit: QtW.QLineEdit
    dir_lineEdit: QtW.QLineEdit
    browse_save_Button: QtW.QPushButton

    channel_groupBox: QtW.QGroupBox
    channel_tableWidget: QtW.QTableWidget  # TODO: extract
    add_ch_Button: QtW.QPushButton
    clear_ch_Button: QtW.QPushButton
    remove_ch_Button: QtW.QPushButton

    time_groupBox: QtW.QGroupBox
    timepoints_spinBox: QtW.QSpinBox
    interval_spinBox: QtW.QSpinBox
    time_comboBox: QtW.QComboBox

    stack_groupBox: QtW.QGroupBox
    step_spinBox: QtW.QSpinBox
    step_size_doubleSpinBox: QtW.QDoubleSpinBox

    stage_pos_groupBox: QtW.QGroupBox
    stage_tableWidget: QtW.QTableWidget  # TODO: extract
    add_pos_Button: QtW.QPushButton
    clear_pos_Button: QtW.QPushButton
    remove_pos_Button: QtW.QPushButton

    acquisition_order_comboBox: QtW.QComboBox
    run_Button: QtW.QPushButton

    # empty_stack_to_viewer = Signal(np.ndarray, str)

    def __init__(self, *args):
        super().__init__(*args)
        uic.loadUi(UI_FILE, self)

        # self.pos_list = []
        # self.pos_stack_list = []
        # self.list_ch = []
        # self.acq_stack_list = []

        # count every time the "Run button is pressed" - define the experiment number
        self.cnt = 0

        # connect buttons
        self.add_pos_Button.clicked.connect(self.add_position)
        self.remove_pos_Button.clicked.connect(self.remove_position)
        self.clear_pos_Button.clicked.connect(self.clear_positions)
        self.add_ch_Button.clicked.connect(self.add_channel)
        self.remove_ch_Button.clicked.connect(self.remove_channel)
        self.clear_ch_Button.clicked.connect(self.clear_channel)

        self.browse_save_Button.clicked.connect(self.set_multi_d_acq_dir)

        self.run_Button.clicked.connect(self._on_run_clicked)

        # connect position table double click
        self.stage_tableWidget.cellDoubleClicked.connect(self.move_to_position)

        # button icon
        self.run_Button.setIcon(QIcon(str(ICONS / "play-button_1.svg")))
        self.run_Button.setIconSize(QSize(20, 0))

    # add, remove, clear channel table
    def add_channel(self):
        dev_loaded = list(mmcore.getLoadedDevices())
        if len(dev_loaded) > 1:

            idx = self.channel_tableWidget.rowCount()
            self.channel_tableWidget.insertRow(idx)

            # create a combo_box for channels in the table
            self.channel_comboBox = QtW.QComboBox(self)
            self.channel_exp_spinBox = QtW.QSpinBox(self)
            self.channel_exp_spinBox.setRange(0, 10000)
            self.channel_exp_spinBox.setValue(100)

            if "Channel" not in mmcore.getAvailableConfigGroups():
                raise ValueError("Could not find 'Channel' in the ConfigGroups")
            channel_list = list(mmcore.getAvailableConfigs("Channel"))
            self.channel_comboBox.addItems(channel_list)

            self.channel_tableWidget.setCellWidget(idx, 0, self.channel_comboBox)
            self.channel_tableWidget.setCellWidget(idx, 1, self.channel_exp_spinBox)

    def remove_channel(self):
        # remove selected position
        rows = {r.row() for r in self.channel_tableWidget.selectedIndexes()}
        for idx in sorted(rows, reverse=True):
            self.channel_tableWidget.removeRow(idx)

    def clear_channel(self):
        # clear all positions
        self.channel_tableWidget.clearContents()
        self.channel_tableWidget.setRowCount(0)

    # add, remove, clear, move_to positions table
    def add_position(self):
        dev_loaded = list(mmcore.getLoadedDevices())
        if len(dev_loaded) > 1:
            x = mmcore.getXPosition()
            y = mmcore.getYPosition()
            z = mmcore.getPosition("Z_Stage")

            x_txt = QtW.QTableWidgetItem(str(x))
            y_txt = QtW.QTableWidgetItem(str(y))
            z_txt = QtW.QTableWidgetItem(str(z))
            x_txt.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            y_txt.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            z_txt.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

            idx = self.stage_tableWidget.rowCount()
            self.stage_tableWidget.insertRow(idx)

            self.stage_tableWidget.setItem(idx, 0, QtW.QTableWidgetItem(x_txt))
            self.stage_tableWidget.setItem(idx, 1, QtW.QTableWidgetItem(y_txt))
            self.stage_tableWidget.setItem(idx, 2, QtW.QTableWidgetItem(z_txt))

    def remove_position(self):
        # remove selected position
        rows = {r.row() for r in self.stage_tableWidget.selectedIndexes()}
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
        # if curr_row != -1:
        x_val = self.stage_tableWidget.item(curr_row, 0).text()
        y_val = self.stage_tableWidget.item(curr_row, 1).text()
        z_val = self.stage_tableWidget.item(curr_row, 2).text()
        # print(f'x: {x_val}')
        # print(f'y: {y_val}')
        # print(f'z: {z_val}')
        mmcore.setXYPosition(float(x_val), float(y_val))
        mmcore.setPosition("Z_Stage", float(z_val))
        print(f"\nStage moved to x:{x_val} y:{y_val} z:{z_val}")

    def set_multi_d_acq_dir(self):
        # set the directory
        self.dir = QtW.QFileDialog(self)
        self.dir.setFileMode(QtW.QFileDialog.DirectoryOnly)
        self.save_dir = QtW.QFileDialog.getExistingDirectory(self.dir)
        self.dir_lineEdit.setText(self.save_dir)
        self.parent_path = Path(self.save_dir)

    # create stack array
    def create_stack_array(self, tp, Zp, nC):  # np.concatenate
        width = mmcore.getROI(mmcore.getCameraDevice())[2]
        height = mmcore.getROI(mmcore.getCameraDevice())[3]
        bitd = mmcore.getProperty(mmcore.getCameraDevice(), "BitDepth")
        dt = f"uint{bitd}"
        mda_stack = np.empty((tp, Zp, nC, height, width), dtype=dt)
        return mda_stack

    def _get_state_dict(self) -> dict:
        state = {
            "acquisition_order": self.acquisition_order_comboBox.currentText(),
            "channels": [],
            "stage_positions": [],
        }
        for c in range(self.channel_tableWidget.rowCount()):
            ch = self.channel_tableWidget.cellWidget(c, 0).currentText()
            exp = self.channel_tableWidget.cellWidget(c, 1).value()
            state["channels"].append((ch, exp))

        # Z settings
        # TODO: restrict the spinbox to >= 1
        if self.stack_groupBox.isChecked():
            n_steps = self.step_spinBox.value()
            stepsize = self.step_size_doubleSpinBox.value()
        else:
            n_steps = 1
            stepsize = 0
        half = stepsize * ((max(1, n_steps) - 1) / 2)
        state["z_positions"] = list(np.linspace(-half, half, n_steps))

        # timelapse settings
        # TODO: restrict nTime to >= 1
        # TODO: restrict interval to >= 1 ms
        nt = self.timepoints_spinBox.value() if self.time_groupBox.isChecked() else 1
        nt = max(1, nt)
        interval = self.interval_spinBox.value()
        # convert interval  ms
        interval *= {"min": 60000, "sec": 1000, "ms": 1}[
            self.time_comboBox.currentText()
        ]
        state["time_deltas"] = list(np.arange(nt) * interval)

        # position settings
        if (
            self.stage_pos_groupBox.isChecked()
            and self.stage_tableWidget.rowCount() > 0
        ):
            for row in range(self.stage_tableWidget.rowCount()):
                xp = float(self.stage_tableWidget.item(row, 0).text())
                yp = float(self.stage_tableWidget.item(row, 1).text())
                zp = float(self.stage_tableWidget.item(row, 2).text())
                state["stage_positions"].append((xp, yp, zp))
        else:
            xp, yp = float(mmcore.getXPosition()), float(mmcore.getYPosition())
            zp = float(mmcore.getPosition("Z_Stage"))
            state["stage_positions"].append((xp, yp, zp))

        return state

    # function is executed when run_Button is clicked
    # (self.run_Button.clicked.connect(self.run))
    def _on_run_clicked(self):
        if len(mmcore.getLoadedDevices()) < 2:
            print("Load a cfg file first.")
            return

        if not self.channel_tableWidget.rowCount() > 0:
            print("Select at least one channel.")
            return

        experiment = MDASequence(**self._get_state_dict())
        mmcore.run_mda(experiment)  # run the MDA acquisition experiment


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication

    app = QApplication([])
    window = MultiDWidget()
    window.show()
    app.exec_()
