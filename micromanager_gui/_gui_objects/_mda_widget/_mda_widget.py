from __future__ import annotations

import warnings
from pathlib import Path
from typing import TYPE_CHECKING

from qtpy import QtWidgets as QtW
from qtpy import uic
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QIcon
from useq import MDASequence

from .._core import get_core_singleton
from .._mda import SEQUENCE_META, SequenceMeta

if TYPE_CHECKING:
    from pymmcore_plus.mda import PMDAEngine

ICONS = Path(__file__).parent.parent / "icons"


class _MultiDUI:
    UI_FILE = str(Path(__file__).parent / "multid_gui.ui")

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
    z_tabWidget: QtW.QTabWidget
    step_size_doubleSpinBox: QtW.QDoubleSpinBox
    n_images_label: QtW.QLabel
    # TopBottom
    set_top_Button: QtW.QPushButton
    set_bottom_Button: QtW.QPushButton
    z_top_doubleSpinBox: QtW.QDoubleSpinBox
    z_bottom_doubleSpinBox: QtW.QDoubleSpinBox
    z_range_topbottom_doubleSpinBox: QtW.QDoubleSpinBox
    # RangeAround
    zrange_spinBox: QtW.QSpinBox
    range_around_label: QtW.QLabel
    # AboveBelow
    above_doubleSpinBox: QtW.QDoubleSpinBox
    below_doubleSpinBox: QtW.QDoubleSpinBox
    z_range_abovebelow_doubleSpinBox: QtW.QDoubleSpinBox

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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

        self._mmc = get_core_singleton()

        self.pause_Button.released.connect(lambda: self._mmc.mda.toggle_pause())
        self.cancel_Button.released.connect(lambda: self._mmc.mda.cancel())

        # connect buttons
        self.add_pos_Button.clicked.connect(self.add_position)
        self.remove_pos_Button.clicked.connect(self.remove_position)
        self.clear_pos_Button.clicked.connect(self.clear_positions)
        self.add_ch_Button.clicked.connect(self.add_channel)
        self.remove_ch_Button.clicked.connect(self.remove_channel)
        self.clear_ch_Button.clicked.connect(self.clear_channel)

        self.browse_save_Button.clicked.connect(self.set_multi_d_acq_dir)
        self.run_Button.clicked.connect(self._on_run_clicked)

        # connect for z stack
        self.set_top_Button.clicked.connect(self._set_top)
        self.set_bottom_Button.clicked.connect(self._set_bottom)
        self.z_top_doubleSpinBox.valueChanged.connect(self._update_topbottom_range)
        self.z_bottom_doubleSpinBox.valueChanged.connect(self._update_topbottom_range)

        self.zrange_spinBox.valueChanged.connect(self._update_rangearound_label)

        self.above_doubleSpinBox.valueChanged.connect(self._update_abovebelow_range)
        self.below_doubleSpinBox.valueChanged.connect(self._update_abovebelow_range)

        self.z_range_abovebelow_doubleSpinBox.valueChanged.connect(
            self._update_n_images
        )
        self.zrange_spinBox.valueChanged.connect(self._update_n_images)
        self.z_range_topbottom_doubleSpinBox.valueChanged.connect(self._update_n_images)
        self.step_size_doubleSpinBox.valueChanged.connect(self._update_n_images)
        self.z_tabWidget.currentChanged.connect(self._update_n_images)
        self.stack_groupBox.toggled.connect(self._update_n_images)

        # toggle connect
        self.save_groupBox.toggled.connect(self.toggle_checkbox_save_pos)
        self.stage_pos_groupBox.toggled.connect(self.toggle_checkbox_save_pos)

        # connect position table double click
        self.stage_tableWidget.cellDoubleClicked.connect(self.move_to_position)

        # events
        self._mmc.mda.events.sequenceStarted.connect(self._on_mda_started)
        self._mmc.mda.events.sequenceFinished.connect(self._on_mda_finished)
        self._mmc.mda.events.sequencePauseToggled.connect(self._on_mda_paused)
        self._mmc.events.mdaEngineRegistered.connect(self._update_mda_engine)

    def _update_mda_engine(self, newEngine: PMDAEngine, oldEngine: PMDAEngine):
        oldEngine.events.sequenceStarted.disconnect(self._on_mda_started)
        oldEngine.events.sequenceFinished.disconnect(self._on_mda_finished)
        oldEngine.events.sequencePauseToggled.disconnect(self._on_mda_paused)

        newEngine.events.sequenceStarted.connect(self._on_mda_started)
        newEngine.events.sequenceFinished.connect(self._on_mda_finished)
        newEngine.events.sequencePauseToggled.connect(self._on_mda_paused)

    def _set_enabled(self, enabled: bool):
        self.save_groupBox.setEnabled(enabled)
        self.time_groupBox.setEnabled(enabled)
        self.acquisition_order_comboBox.setEnabled(enabled)
        self.channel_groupBox.setEnabled(enabled)

        if not self._mmc.getXYStageDevice():
            self.stage_pos_groupBox.setChecked(False)
            self.stage_pos_groupBox.setEnabled(False)
        else:
            self.stage_pos_groupBox.setEnabled(enabled)

        if not self._mmc.getFocusDevice():
            self.stack_groupBox.setChecked(False)
            self.stack_groupBox.setEnabled(False)
        else:
            self.stack_groupBox.setEnabled(enabled)

    def _set_top(self):
        self.z_top_doubleSpinBox.setValue(self._mmc.getZPosition())

    def _set_bottom(self):
        self.z_bottom_doubleSpinBox.setValue(self._mmc.getZPosition())

    def _update_topbottom_range(self):
        self.z_range_topbottom_doubleSpinBox.setValue(
            abs(self.z_top_doubleSpinBox.value() - self.z_bottom_doubleSpinBox.value())
        )

    def _update_rangearound_label(self, value):
        self.range_around_label.setText(f"-{value/2} µm <- z -> +{value/2} µm")

    def _update_abovebelow_range(self):
        self.z_range_abovebelow_doubleSpinBox.setValue(
            self.above_doubleSpinBox.value() + self.below_doubleSpinBox.value()
        )

    def _update_n_images(self):
        step = self.step_size_doubleSpinBox.value()
        # set what is the range to consider depending on the z_stack mode
        if self.z_tabWidget.currentIndex() == 0:
            range = self.z_range_topbottom_doubleSpinBox.value()
        if self.z_tabWidget.currentIndex() == 1:
            range = self.zrange_spinBox.value()
        if self.z_tabWidget.currentIndex() == 2:
            range = self.z_range_abovebelow_doubleSpinBox.value()

        self.n_images_label.setText(f"{round((range / step) + 1)}")

    def _on_mda_started(self, sequence):
        self._set_enabled(False)
        self.pause_Button.show()
        self.cancel_Button.show()
        self.run_Button.hide()

    def _on_mda_finished(self, sequence):
        self._set_enabled(True)
        self.pause_Button.hide()
        self.cancel_Button.hide()
        self.run_Button.show()

    def _on_mda_paused(self, paused):
        self.pause_Button.setText("GO" if paused else "PAUSE")

    # add, remove, clear channel table
    def add_channel(self) -> bool:
        if len(self._mmc.getLoadedDevices()) <= 1:
            return False

        channel_group = self._mmc.getChannelGroup()
        if not channel_group:
            return

        idx = self.channel_tableWidget.rowCount()
        self.channel_tableWidget.insertRow(idx)

        # create a combo_box for channels in the table
        channel_comboBox = QtW.QComboBox(self)
        channel_exp_spinBox = QtW.QSpinBox(self)
        channel_exp_spinBox.setRange(0, 10000)
        channel_exp_spinBox.setValue(100)

        if channel_group := self._mmc.getChannelGroup():
            channel_list = list(self._mmc.getAvailableConfigs(channel_group))
            channel_comboBox.addItems(channel_list)

        self.channel_tableWidget.setCellWidget(idx, 0, channel_comboBox)
        self.channel_tableWidget.setCellWidget(idx, 1, channel_exp_spinBox)
        return True

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
            self.checkBox_save_pos.setCheckState(Qt.CheckState.Unchecked)
            self.checkBox_save_pos.setEnabled(False)

    # add, remove, clear, move_to positions table
    def add_position(self):

        if not self._mmc.getXYStageDevice():
            return

        if len(self._mmc.getLoadedDevices()) > 1:
            idx = self._add_position_row()

            for c, ax in enumerate("XYZ"):
                if not self._mmc.getFocusDevice() and ax == "Z":
                    continue
                cur = getattr(self._mmc, f"get{ax}Position")()
                item = QtW.QTableWidgetItem(str(cur))
                item.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
                self.stage_tableWidget.setItem(idx, c, item)

            self.toggle_checkbox_save_pos()

    def _add_position_row(self) -> int:
        idx = self.stage_tableWidget.rowCount()
        self.stage_tableWidget.insertRow(idx)
        return idx

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
        if not self._mmc.getXYStageDevice():
            return
        curr_row = self.stage_tableWidget.currentRow()
        x_val = self.stage_tableWidget.item(curr_row, 0).text()
        y_val = self.stage_tableWidget.item(curr_row, 1).text()
        z_val = self.stage_tableWidget.item(curr_row, 2).text()
        self._mmc.setXYPosition(float(x_val), float(y_val))
        self._mmc.setPosition(self._mmc.getFocusDevice(), float(z_val))

    def set_multi_d_acq_dir(self):
        # set the directory
        self.dir = QtW.QFileDialog(self)
        self.dir.setFileMode(QtW.QFileDialog.DirectoryOnly)
        self.save_dir = QtW.QFileDialog.getExistingDirectory(self.dir)
        self.dir_lineEdit.setText(self.save_dir)
        self.parent_path = Path(self.save_dir)

    def set_state(self, state: dict | MDASequence | str | Path) -> None:
        """Set current state of MDA widget.

        Parameters
        ----------
        state : Union[dict, MDASequence, str, Path]
            MDASequence state in the form of a dict, MDASequence object, or a str or
            Path pointing to a sequence.yaml file
        """
        if isinstance(state, (str, Path)):
            state = MDASequence.parse_file(state)
        elif isinstance(state, dict):
            state = MDASequence(**state)
        if not isinstance(state, MDASequence):
            raise TypeError("state must be an MDASequence, dict, or yaml file")

        self.acquisition_order_comboBox.setCurrentText(state.axis_order)

        # set channel table
        self.clear_channel()
        if channel_group := self._mmc.getChannelGroup():
            channel_list = list(self._mmc.getAvailableConfigs(channel_group))
        else:
            channel_list = []
        for idx, ch in enumerate(state.channels):
            if not self.add_channel():
                break
            if ch.config in channel_list:
                self.channel_tableWidget.cellWidget(idx, 0).setCurrentText(ch.config)
            else:
                warnings.warn(
                    f"Unrecognized channel: {ch.config!r}. "
                    f"Valid channels include {channel_list}"
                )
            if ch.exposure:
                self.channel_tableWidget.cellWidget(idx, 1).setValue(int(ch.exposure))

        # set Z
        if state.z_plan:
            self.stack_groupBox.setChecked(True)
            if hasattr(state.z_plan, "top") and hasattr(state.z_plan, "bottom"):
                self.z_top_doubleSpinBox.setValue(state.z_plan.top)
                self.z_bottom_doubleSpinBox.setValue(state.z_plan.bottom)
                self.z_tabWidget.setCurrentIndex(0)
            elif hasattr(state.z_plan, "above") and hasattr(state.z_plan, "below"):
                self.above_doubleSpinBox.setValue(state.z_plan.above)
                self.below_doubleSpinBox.setValue(state.z_plan.below)
                self.z_tabWidget.setCurrentIndex(2)
            elif hasattr(state.z_plan, "range"):
                self.zrange_spinBox.setValue(int(state.z_plan.range))
                self.z_tabWidget.setCurrentIndex(1)
            if hasattr(state.z_plan, "step"):
                self.step_size_doubleSpinBox.setValue(state.z_plan.step)
        else:
            self.stack_groupBox.setChecked(False)

        # set time
        # currently only `TIntervalLoops` is supported
        if hasattr(state.time_plan, "interval") and hasattr(state.time_plan, "loops"):
            self.time_groupBox.setChecked(True)
            self.timepoints_spinBox.setValue(state.time_plan.loops)

            sec = state.time_plan.interval.total_seconds()
            if sec >= 60:
                self.time_comboBox.setCurrentText("min")
                self.interval_spinBox.setValue(sec // 60)
            elif sec >= 1:
                self.time_comboBox.setCurrentText("sec")
                self.interval_spinBox.setValue(int(sec))
            else:
                self.time_comboBox.setCurrentText("ms")
                self.interval_spinBox.setValue(int(sec * 1000))
        else:
            self.time_groupBox.setChecked(False)

        # set stage positions
        self.clear_positions()
        if state.stage_positions:
            self.stage_pos_groupBox.setChecked(True)
            for idx, pos in enumerate(state.stage_positions):
                self._add_position_row()
                for c, ax in enumerate("xyz"):
                    item = QtW.QTableWidgetItem(str(getattr(pos, ax)))
                    item.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
                    self.stage_tableWidget.setItem(idx, c, item)
        else:
            self.stage_pos_groupBox.setChecked(False)

    def get_state(self) -> MDASequence:
        """Get current state of widget as a useq.MDASequence."""
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

            if self.z_tabWidget.currentIndex() == 0:
                state["z_plan"] = {
                    "top": self.z_top_doubleSpinBox.value(),
                    "bottom": self.z_bottom_doubleSpinBox.value(),
                    "step": self.step_size_doubleSpinBox.value(),
                }

            elif self.z_tabWidget.currentIndex() == 1:
                state["z_plan"] = {
                    "range": self.zrange_spinBox.value(),
                    "step": self.step_size_doubleSpinBox.value(),
                }
            elif self.z_tabWidget.currentIndex() == 2:
                state["z_plan"] = {
                    "above": self.above_doubleSpinBox.value(),
                    "below": self.below_doubleSpinBox.value(),
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
        if self._mmc.getXYStageDevice():
            if (
                self.stage_pos_groupBox.isChecked()
                and self.stage_tableWidget.rowCount() > 0
            ):
                for r in range(self.stage_tableWidget.rowCount()):
                    pos = {
                        "x": float(self.stage_tableWidget.item(r, 0).text()),
                        "y": float(self.stage_tableWidget.item(r, 1).text()),
                    }
                    if self._mmc.getFocusDevice():
                        pos["z"] = float(self.stage_tableWidget.item(r, 2).text())
                    state["stage_positions"].append(pos)
            else:
                pos = {
                    "x": float(self._mmc.getXPosition()),
                    "y": float(self._mmc.getYPosition()),
                }
                if self._mmc.getFocusDevice():
                    pos["z"] = float(self._mmc.getZPosition())
                state["stage_positions"].append(pos)

        return MDASequence(**state)

    def _on_run_clicked(self):

        if len(self._mmc.getLoadedDevices()) < 2:
            raise ValueError("Load a cfg file first.")

        if self.channel_tableWidget.rowCount() <= 0:
            raise ValueError("Select at least one channel.")

        if self.stage_pos_groupBox.isChecked() and (
            self.stage_tableWidget.rowCount() <= 0
        ):
            raise ValueError(
                "Select at least one position" "or deselect the position groupbox."
            )

        if self.save_groupBox.isChecked() and not (
            self.fname_lineEdit.text() and Path(self.dir_lineEdit.text()).is_dir()
        ):
            raise ValueError("Select a filename and a valid directory.")

        experiment = self.get_state()

        SEQUENCE_META[experiment] = SequenceMeta(
            mode="mda",
            split_channels=self.checkBox_split_channels.isChecked(),
            should_save=self.save_groupBox.isChecked(),
            file_name=self.fname_lineEdit.text(),
            save_dir=self.dir_lineEdit.text(),
            save_pos=self.checkBox_save_pos.isChecked(),
        )
        self._mmc.run_mda(experiment)  # run the MDA experiment asynchronously
        return


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication

    app = QApplication([])
    window = MultiDWidget()
    window.show()
    app.exec_()
