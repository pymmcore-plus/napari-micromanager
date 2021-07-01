from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from qtpy import QtWidgets as QtW
from qtpy import uic
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QIcon
from useq import MDASequence

if TYPE_CHECKING:
    from pymmcore_remote import RemoteMMCore

ICONS = Path(__file__).parent / "icons"


class _MultiDUI:
    UI_FILE = str(Path(__file__).parent / "_ui" / "multid_gui.ui")

    # The UI_FILE above contains these objects:
    save_groupBox: QtW.QGroupBox
    fname_lineEdit: QtW.QLineEdit
    dir_lineEdit: QtW.QLineEdit
    browse_save_Button: QtW.QPushButton
    checkBox_save_pos: QtW.QCheckBox
    checkBox_split_channels: QtW.QCheckBox

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
    zrange_spinBox: QtW.QSpinBox
    step_size_doubleSpinBox: QtW.QDoubleSpinBox

    stage_pos_groupBox: QtW.QGroupBox
    stage_tableWidget: QtW.QTableWidget  # TODO: extract
    add_pos_Button: QtW.QPushButton
    clear_pos_Button: QtW.QPushButton
    remove_pos_Button: QtW.QPushButton

    acquisition_order_comboBox: QtW.QComboBox
    run_Button: QtW.QPushButton
    pause_Button: QtW.QPushButton
    cancel_Button: QtW.QPushButton

    def setup_ui(self):
        uic.loadUi(self.UI_FILE, self)  # load QtDesigner .ui file
        self.pause_Button.hide()
        self.cancel_Button.hide()
        # button icon
        self.run_Button.setIcon(QIcon(str(ICONS / "play-button_1.svg")))
        self.run_Button.setIconSize(QSize(20, 0))


class MultiDWidget(QtW.QWidget, _MultiDUI):

    # TODO: don't love passing `signals` here...
    def __init__(self, mmcore: RemoteMMCore, parent=None):
        self._mmc = mmcore
        super().__init__(parent)
        self.setup_ui()

        self.pause_Button.released.connect(self._mmc.toggle_pause)
        self.cancel_Button.released.connect(self._mmc.cancel)

        # connect buttons
        self.add_pos_Button.clicked.connect(self.add_position)
        self.remove_pos_Button.clicked.connect(self.remove_position)
        self.clear_pos_Button.clicked.connect(self.clear_positions)
        self.add_ch_Button.clicked.connect(self.add_channel)
        self.remove_ch_Button.clicked.connect(self.remove_channel)
        self.clear_ch_Button.clicked.connect(self.clear_channel)

        self.browse_save_Button.clicked.connect(self.set_multi_d_acq_dir)
        self.run_Button.clicked.connect(self._on_run_clicked)

        # toggle connect
        self.save_groupBox.toggled.connect(self.toggle_checkbox_save_pos)
        self.stage_pos_groupBox.toggled.connect(self.toggle_checkbox_save_pos)

        # connect position table double click
        self.stage_tableWidget.cellDoubleClicked.connect(self.move_to_position)

    def enable_mda_groupbox(self):
        self.save_groupBox.setEnabled(True)
        self.channel_groupBox.setEnabled(True)
        self.time_groupBox.setEnabled(True)
        self.stack_groupBox.setEnabled(True)
        self.stage_pos_groupBox.setEnabled(True)
        self.acquisition_order_comboBox.setEnabled(True)

    def disable_mda_groupbox(self):
        self.save_groupBox.setEnabled(False)
        self.channel_groupBox.setEnabled(False)
        self.time_groupBox.setEnabled(False)
        self.stack_groupBox.setEnabled(False)
        self.stage_pos_groupBox.setEnabled(False)
        self.acquisition_order_comboBox.setEnabled(False)

    def _on_mda_started(self, sequence):
        self.pause_Button.show()
        self.cancel_Button.show()
        self.run_Button.hide()

    def _on_mda_finished(self):
        self.pause_Button.hide()
        self.cancel_Button.hide()
        self.run_Button.show()

    # add, remove, clear channel table
    def add_channel(self):
        dev_loaded = list(self._mmc.getLoadedDevices())
        if len(dev_loaded) > 1:

            idx = self.channel_tableWidget.rowCount()
            self.channel_tableWidget.insertRow(idx)

            # create a combo_box for channels in the table
            self.channel_comboBox = QtW.QComboBox(self)
            self.channel_exp_spinBox = QtW.QSpinBox(self)
            self.channel_exp_spinBox.setRange(0, 10000)
            self.channel_exp_spinBox.setValue(100)

            if "Channel" not in self._mmc.getAvailableConfigGroups():
                raise ValueError("Could not find 'Channel' in the ConfigGroups")
            channel_list = list(self._mmc.getAvailableConfigs("Channel"))
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

    def toggle_checkbox_save_pos(self):
        if (
            self.stage_pos_groupBox.isChecked()
            and self.stage_tableWidget.rowCount() > 0
        ):
            self.checkBox_save_pos.setEnabled(True)

        else:
            self.checkBox_save_pos.setCheckState(False)
            self.checkBox_save_pos.setEnabled(False)

    # add, remove, clear, move_to positions table
    def add_position(self):
        dev_loaded = list(self._mmc.getLoadedDevices())
        if len(dev_loaded) > 1:
            x = self._mmc.getXPosition()
            y = self._mmc.getYPosition()
            z = self._mmc.getZPosition()

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

            self.toggle_checkbox_save_pos()

    def remove_position(self):
        # remove selected position
        rows = {r.row() for r in self.stage_tableWidget.selectedIndexes()}
        for idx in sorted(rows, reverse=True):
            self.stage_tableWidget.removeRow(idx)
        self.toggle_checkbox_save_pos()

    def clear_positions(self):
        # clear all positions
        self.stage_tableWidget.clearContents()
        self.stage_tableWidget.setRowCount(0)
        self.toggle_checkbox_save_pos()

    def move_to_position(self):
        curr_row = self.stage_tableWidget.currentRow()
        x_val = self.stage_tableWidget.item(curr_row, 0).text()
        y_val = self.stage_tableWidget.item(curr_row, 1).text()
        z_val = self.stage_tableWidget.item(curr_row, 2).text()
        self._mmc.setXYPosition(float(x_val), float(y_val))
        self._mmc.setPosition("Z_Stage", float(z_val))
        print(f"\nStage moved to x:{x_val} y:{y_val} z:{z_val}")

    def set_multi_d_acq_dir(self):
        # set the directory
        self.dir = QtW.QFileDialog(self)
        self.dir.setFileMode(QtW.QFileDialog.DirectoryOnly)
        self.save_dir = QtW.QFileDialog.getExistingDirectory(self.dir)
        self.dir_lineEdit.setText(self.save_dir)
        self.parent_path = Path(self.save_dir)

    def _get_state_dict(self) -> dict:
        state = {
            "axis_order": self.acquisition_order_comboBox.currentText(),
            "channels": [],
            "stage_positions": [],
            "z_plan": None,
            "time_plan": None,
        }
        state["channels"] = [
            {
                "config": self.channel_tableWidget.cellWidget(c, 0).currentText(),
                "group": self._mmc.getChannelGroup() or "Channel",
                "exposure": self.channel_tableWidget.cellWidget(c, 1).value(),
            }
            for c in range(self.channel_tableWidget.rowCount())
        ]
        if self.stack_groupBox.isChecked():
            state["z_plan"] = {
                "range": self.zrange_spinBox.value(),
                "step": self.step_size_doubleSpinBox.value(),
            }
        if self.time_groupBox.isChecked():
            unit = {"min": "minutes", "sec": "seconds", "ms": "milliseconds"}[
                self.time_comboBox.currentText()
            ]
            state["time_plan"] = {
                "interval": {unit: self.interval_spinBox.value()},
                "loops": self.timepoints_spinBox.value(),
            }
        # position settings
        if (
            self.stage_pos_groupBox.isChecked()
            and self.stage_tableWidget.rowCount() > 0
        ):
            for r in range(self.stage_tableWidget.rowCount()):
                state["stage_positions"].append(
                    {
                        "x": float(self.stage_tableWidget.item(r, 0).text()),
                        "y": float(self.stage_tableWidget.item(r, 1).text()),
                        "z": float(self.stage_tableWidget.item(r, 2).text()),
                    }
                )
        else:
            state["stage_positions"].append(
                {
                    "x": float(self._mmc.getXPosition()),
                    "y": float(self._mmc.getYPosition()),
                    "z": float(self._mmc.getZPosition()),
                }
            )

        return state

    def _on_run_clicked(self):
        from .main_window import SEQUENCE_META

        if len(self._mmc.getLoadedDevices()) < 2:
            raise ValueError("Load a cfg file first.")

        if self.channel_tableWidget.rowCount() <= 0:
            raise ValueError("Select at least one channel.")

        if self.stage_pos_groupBox.isChecked() and (
            self.stage_tableWidget.rowCount() <= 0
        ):
            raise ValueError("Select at least one position"
                             "or deselect the position groupbox.")

        if self.save_groupBox.isChecked() and (
            self.fname_lineEdit.text() == ""
            or (
                self.dir_lineEdit.text() == ""
                or not Path.is_dir(Path(self.dir_lineEdit.text()))
            )
        ):
            raise ValueError("select a filename and a valid directory.")

        experiment = MDASequence(**self._get_state_dict())

        SEQUENCE_META[experiment] = {
            "mode": 'mda',
            "split_channels": self.checkBox_split_channels.isChecked(),
            "save_group_mda": self.save_groupBox.isChecked(),
            "file_name": self.fname_lineEdit.text(),
            "save_dir": self.dir_lineEdit.text(),
            "save_pos": self.checkBox_save_pos.isChecked(),
        }

        self._mmc.run_mda(experiment)  # run the MDA experiment asynchronously
        return


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication

    app = QApplication([])
    window = MultiDWidget()
    window.show()
    app.exec_()
