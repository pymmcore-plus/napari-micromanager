from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple, Tuple

import numpy as np
from PyQt5 import QtCore
from PyQt5 import QtWidgets as QtW
from PyQt5.QtGui import QIcon
from qtpy import uic
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QFileDialog

from .mmcore_pymmcore import MMCore

icon_path = Path(__file__).parent / "icons"

UI_FILE = str(Path(__file__).parent / "multid_gui.ui")

mmcore = MMCore()


class Frame(NamedTuple):
    t: int  # (desired) msec from start of experiment
    c: Tuple[str, int]  # tuple of channel name, exposure time
    z: float  # z positions (around middle)
    p: Tuple[float, float, float]  # middle stage position (x,y,z)

    def __str__(self):
        ch, exp = self.c
        x, y, z = self.p
        z += self.z
        return f"t{self.t}, pos<{x}, {y}, {z}>, channel {ch} {exp}ms"


@dataclass(frozen=True)
class MultiDExperiment:
    acquisition_order: str = "tpcz"
    channels: Tuple[Tuple[str, int]] = field(default_factory=tuple)
    stage_positions: Tuple[Tuple[float, float, float]] = field(default_factory=tuple)
    time_deltas: Tuple[int] = field(default_factory=tuple)
    z_positions: Tuple[float] = field(default_factory=tuple)

    def __str__(self):
        out = "Multi-Dimensional Acquisition ▶ "
        shape = [
            f"n{k.upper()}: {len(self._axes_dict[k])}" for k in self.acquisition_order
        ]
        out += ", ".join(shape)
        return out

    def __len__(self):
        return np.prod(self.shape)

    @property
    def shape(self) -> Tuple[int]:
        return tuple(len(self._axes_dict[k]) for k in self.acquisition_order)

    @property
    def _axes_dict(self):
        return {
            "c": self.channels,
            "z": self.z_positions,
            "p": self.stage_positions,
            "t": self.time_deltas,
        }

    def __iter__(self):
        yield from self.iter_axes(self.acquisition_order)

    def iter_axes(self, order: str = None):
        from itertools import product

        order = order if order else self.acquisition_order
        order = order.lower()
        extra = {x for x in order if x not in "tpcz"}
        if extra:
            raise ValueError(
                f"Can only iterate over axes: t, p, z, c.  Got extra: {extra}"
            )
        if len(set(order)) < len(order):
            raise ValueError(f"Duplicate entries found in acquisition order: {order}")

        for item in product(*(self._axes_dict[ax] for ax in order)):
            # print(f'frame: {Frame(**dict(zip(order, item)))}')
            yield Frame(**dict(zip(order, item)))


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
    timepoints_spinBox: QtW.QSpinBox
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

        self.run_Button.clicked.connect(self.run)

        # connect position table double click
        self.stage_tableWidget.cellDoubleClicked.connect(self.move_to_position)

        # button icon
        self.run_Button.setIcon(QIcon(str(icon_path / "play-button_1.svg")))
        self.run_Button.setIconSize(QtCore.QSize(20, 20))

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
        self.dir = QFileDialog(self)
        self.dir.setFileMode(QFileDialog.DirectoryOnly)
        self.save_dir = QFileDialog.getExistingDirectory(self.dir)
        self.dir_lineEdit.setText(self.save_dir)
        self.parent_path = Path(self.save_dir)

    # TODO: go back to threading in a bit...
    # def acquisition_order(self):
    #     if self.acquisition_order_comboBox.currentText()=='tpzcxy':
    #         with concurrent.futures.ThreadPoolExecutor() as executor:
    #             executor.submit(self.run_multi_d_acq_tpzcxy())
    #     #elif:

    def mda_summary_string(self):
        pass

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

    # function is exequted when run_Button is clicked
    # (self.run_Button.clicked.connect(self.run))
    def run(self):

        self.cnt = (
            self.cnt + 1
        )  # count every time the "Run button is pressed" - define the experiment number

        nC = self.channel_tableWidget.rowCount()  # n of channels
        Tp = (
            self.timepoints_spinBox.value() if self.time_groupBox.isChecked() else 1
        )  # n of timepoints
        Zp = (
            self.step_spinBox.value() if self.stack_groupBox.isChecked() else 1
        )  # n of z steps

        stack = self.create_stack_array(
            Tp, Zp, nC
        )  # create empty stack to use in mmcore.run_mda(...)

        experiment = MultiDExperiment(**self._get_state_dict())

        mmcore.run_mda(
            experiment, stack, self.cnt
        )  # run the MDA acquisition experiment


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication

    app = QApplication([])
    window = MultiDWidget()
    window.show()
    app.exec_()
