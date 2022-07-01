from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

import useq
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt
from useq import MDASequence

from micromanager_gui import _mda

from ..._core import get_core_singleton
from ..._gui_objects._sample_explorer_widget._sample_explorer_gui import ExplorerGui

if TYPE_CHECKING:
    from pymmcore_plus.mda import PMDAEngine


UI_FILE = str(Path(__file__).parent / "explore_sample.ui")


class MMExploreSample(ExplorerGui):
    """Widget to create/run tiled acquisitions."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._mmc = get_core_singleton()

        self.pixel_size = 0

        self.return_to_position_x = None
        self.return_to_position_y = None

        # connect for channel
        self.add_ch_explorer_Button.clicked.connect(self.add_channel)
        self.remove_ch_explorer_Button.clicked.connect(self.remove_channel)
        self.clear_ch_explorer_Button.clicked.connect(self.clear_channel)

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

        # connect for positions
        self.add_pos_Button.clicked.connect(self.add_position)
        self.remove_pos_Button.clicked.connect(self.remove_position)
        self.clear_pos_Button.clicked.connect(self.clear_positions)
        self.stage_tableWidget.cellDoubleClicked.connect(self.move_to_position)

        # connect buttons
        self.start_scan_Button.clicked.connect(self.start_scan)
        self.move_to_Button.clicked.connect(self.move_to)
        self.browse_save_explorer_Button.clicked.connect(self.set_explorer_dir)

        self.stop_scan_Button.clicked.connect(lambda e: self._mmc.mda.cancel())

        self.x_lineEdit.setText(str(None))
        self.y_lineEdit.setText(str(None))

        # connect mmcore signals
        self._mmc.events.systemConfigurationLoaded.connect(self.clear_channel)

        self._mmc.mda.events.sequenceStarted.connect(self._on_mda_started)
        self._mmc.mda.events.sequenceFinished.connect(self._on_mda_finished)

        self._mmc.events.mdaEngineRegistered.connect(self._update_mda_engine)

    def _update_mda_engine(self, newEngine: PMDAEngine, oldEngine: PMDAEngine):
        oldEngine.events.sequenceStarted.disconnect(self._on_mda_started)
        oldEngine.events.sequenceFinished.disconnect(self._on_mda_finished)

        newEngine.events.sequenceStarted.connect(self._on_mda_started)
        newEngine.events.sequenceFinished.connect(self._on_mda_finished)

    def _on_mda_started(self, sequence: useq.MDASequence):
        """Block gui when mda starts."""
        self._set_enabled(False)

    def _on_mda_finished(self, sequence: useq.MDASequence):
        # TODO: have this widget be able to save independently of napari
        # meta = _mda.SEQUENCE_META.pop(sequence, _mda.SequenceMeta())
        # save_sequence(sequence, self.viewer.layers, meta)
        meta = _mda.SEQUENCE_META.get(sequence, _mda.SequenceMeta())
        if meta.mode == "explorer" and (
            self.return_to_position_x is not None
            and self.return_to_position_y is not None
        ):
            self._mmc.setXYPosition(
                self.return_to_position_x, self.return_to_position_y
            )
            self.return_to_position_x = None
            self.return_to_position_y = None
        self._set_enabled(True)

    def _set_enabled(self, enabled):
        self.save_explorer_groupBox.setEnabled(enabled)
        self.scan_size_spinBox_r.setEnabled(enabled)
        self.scan_size_spinBox_c.setEnabled(enabled)
        self.ovelap_spinBox.setEnabled(enabled)
        self.move_to_Button.setEnabled(enabled)
        self.start_scan_Button.setEnabled(enabled)
        self.channel_explorer_groupBox.setEnabled(enabled)

    # add, remove, clear channel table
    def add_channel(self):
        dev_loaded = list(self._mmc.getLoadedDevices())
        if len(dev_loaded) > 1:

            if not self._mmc.getXYStageDevice():
                return

            channel_group = self._mmc.getChannelGroup()
            if not channel_group:
                return

            idx = self.channel_explorer_tableWidget.rowCount()
            self.channel_explorer_tableWidget.insertRow(idx)

            # create a combo_box for channels in the table
            self.channel_explorer_comboBox = QtW.QComboBox(self)
            self.channel_explorer_exp_spinBox = QtW.QSpinBox(self)
            self.channel_explorer_exp_spinBox.setRange(0, 10000)
            self.channel_explorer_exp_spinBox.setValue(100)

            channel_list = list(self._mmc.getAvailableConfigs(channel_group))
            self.channel_explorer_comboBox.addItems(channel_list)

            self.channel_explorer_tableWidget.setCellWidget(
                idx, 0, self.channel_explorer_comboBox
            )
            self.channel_explorer_tableWidget.setCellWidget(
                idx, 1, self.channel_explorer_exp_spinBox
            )

    def remove_channel(self):
        # remove selected position
        rows = {r.row() for r in self.channel_explorer_tableWidget.selectedIndexes()}
        for idx in sorted(rows, reverse=True):
            self.channel_explorer_tableWidget.removeRow(idx)

    def clear_channel(self):
        # clear all positions
        self.channel_explorer_tableWidget.clearContents()
        self.channel_explorer_tableWidget.setRowCount(0)

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
            _range = self.z_range_topbottom_doubleSpinBox.value()
        if self.z_tabWidget.currentIndex() == 1:
            _range = self.zrange_spinBox.value()
        if self.z_tabWidget.currentIndex() == 2:
            _range = self.z_range_abovebelow_doubleSpinBox.value()

        self.n_images_label.setText(f"Number of Images: {round((_range / step) + 1)}")

    # add, remove, clear, move_to positions table
    def add_position(self):

        if not self._mmc.getXYStageDevice():
            return

        if len(self._mmc.getLoadedDevices()) > 1:
            idx = self._add_position_row()

            for c, ax in enumerate("GXYZ"):
                if ax == "G":
                    count = self.stage_tableWidget.rowCount()
                    item = QtW.QTableWidgetItem(f"Grid_{count:03d}")
                    item.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
                    self.stage_tableWidget.setItem(idx, c, item)
                    continue

                if not self._mmc.getFocusDevice() and ax == "Z":
                    continue

                cur = getattr(self._mmc, f"get{ax}Position")()
                item = QtW.QTableWidgetItem(str(cur))
                item.setTextAlignment(int(Qt.AlignHCenter | Qt.AlignVCenter))
                self.stage_tableWidget.setItem(idx, c, item)

    def _add_position_row(self) -> int:
        idx = self.stage_tableWidget.rowCount()
        self.stage_tableWidget.insertRow(idx)
        return idx

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
        if not self._mmc.getXYStageDevice():
            return
        curr_row = self.stage_tableWidget.currentRow()
        x_val = self.stage_tableWidget.item(curr_row, 1).text()
        y_val = self.stage_tableWidget.item(curr_row, 2).text()
        z_val = self.stage_tableWidget.item(curr_row, 3).text()
        self._mmc.setXYPosition(float(x_val), float(y_val))
        self._mmc.setPosition(self._mmc.getFocusDevice(), float(z_val))

    def _get_state_dict(self) -> dict:

        table = self.channel_explorer_tableWidget

        state = {
            "axis_order": "tpzc",
            "channels": [],
            "stage_positions": [],
            "z_plan": None,
            "time_plan": None,
        }

        state["channels"] = [
            {  # type: ignore
                "config": table.cellWidget(c, 0).currentText(),
                "group": self._mmc.getChannelGroup() or "Channel",
                "exposure": table.cellWidget(c, 1).value(),
            }
            for c in range(table.rowCount())
        ]

        if self.stack_groupBox.isChecked():

            if self.z_tabWidget.currentIndex() == 0:
                state["z_plan"] = {  # type: ignore
                    "top": self.z_top_doubleSpinBox.value(),
                    "bottom": self.z_bottom_doubleSpinBox.value(),
                    "step": self.step_size_doubleSpinBox.value(),
                }

            elif self.z_tabWidget.currentIndex() == 1:
                state["z_plan"] = {  # type: ignore
                    "range": self.zrange_spinBox.value(),
                    "step": self.step_size_doubleSpinBox.value(),
                }
            elif self.z_tabWidget.currentIndex() == 2:
                state["z_plan"] = {  # type: ignore
                    "above": self.above_doubleSpinBox.value(),
                    "below": self.below_doubleSpinBox.value(),
                    "step": self.step_size_doubleSpinBox.value(),
                }

        if self.time_groupBox.isChecked():
            unit = {"min": "minutes", "sec": "seconds", "ms": "milliseconds"}[
                self.time_comboBox.currentText()
            ]
            state["time_plan"] = {  # type: ignore
                "interval": {unit: self.interval_spinBox.value()},
                "loops": self.timepoints_spinBox.value(),
            }

        for g in self.set_grid():
            pos = {"name": g[0], "x": g[1], "y": g[2]}
            if len(g) == 4:
                pos["z"] = g[3]
            state["stage_positions"].append(pos)  # type: ignore

        return state

    def set_grid(self) -> list[tuple[str, float, float, Optional[float]]]:

        self.scan_size_r = self.scan_size_spinBox_r.value()
        self.scan_size_c = self.scan_size_spinBox_c.value()
        self.pixel_size = self._mmc.getPixelSizeUm()

        explorer_starting_positions = []
        if (
            self.stage_pos_groupBox.isChecked()
            and self.stage_tableWidget.rowCount() > 0
        ):
            for r in range(self.stage_tableWidget.rowCount()):
                name = self.stage_tableWidget.item(r, 0).text()
                x = float(self.stage_tableWidget.item(r, 1).text())
                y = float(self.stage_tableWidget.item(r, 2).text())
                z = float(self.stage_tableWidget.item(r, 3).text())
                pos_info = (
                    (name, x, y, z) if self._mmc.getFocusDevice() else (name, x, y)
                )
                explorer_starting_positions.append(pos_info)

        else:
            name = "Grid_001"
            x = float(self._mmc.getXPosition())
            y = float(self._mmc.getYPosition())
            if self._mmc.getFocusDevice():
                z = float(self._mmc.getZPosition())
                pos_info = (name, x, y, z)
            else:
                pos_info = (name, x, y)
            explorer_starting_positions.append(pos_info)

        full_pos_list = []
        for pe in explorer_starting_positions:

            name, x_pos, y_pos = pe[0], pe[1], pe[2]
            if self._mmc.getFocusDevice():
                z_pos = pe[3]

            self.return_to_position_x = x_pos
            self.return_to_position_y = y_pos

            # calculate initial scan position
            _, _, width, height = self._mmc.getROI(self._mmc.getCameraDevice())

            overlap_percentage = self.ovelap_spinBox.value()
            overlap_px_w = width - (width * overlap_percentage) / 100
            overlap_px_h = height - (height * overlap_percentage) / 100

            if self.scan_size_r == 1 and self.scan_size_c == 1:
                raise ValueError(
                    "RxC -> 1x1. Use MDA to acquire a single position image."
                )

            move_x = (width / 2) * (self.scan_size_c - 1) - overlap_px_w
            move_y = (height / 2) * (self.scan_size_r - 1) - overlap_px_h

            # to match position coordinates with center of the image
            x_pos -= self.pixel_size * (move_x + width)
            y_pos += self.pixel_size * (move_y + height)

            # calculate position increments depending on pixle size
            if overlap_percentage > 0:
                increment_x = overlap_px_w * self.pixel_size
                increment_y = overlap_px_h * self.pixel_size
            else:
                increment_x = width * self.pixel_size
                increment_y = height * self.pixel_size

            list_pos_order = []
            pos_count = 0
            for r in range(self.scan_size_r):
                if r % 2:  # for odd rows
                    col = self.scan_size_c - 1
                    for c in range(self.scan_size_c):
                        if c == 0:
                            y_pos -= increment_y
                        pos_name = f"{name}_Pos{pos_count:03d}"
                        if self._mmc.getFocusDevice():
                            list_pos_order.append((pos_name, x_pos, y_pos, z_pos))
                        else:
                            list_pos_order.append(
                                (pos_name, x_pos, y_pos)  # type: ignore
                            )
                        if col > 0:
                            col -= 1
                            x_pos -= increment_x
                        pos_count += 1
                else:  # for even rows
                    for c in range(self.scan_size_c):
                        if r > 0 and c == 0:
                            y_pos -= increment_y
                        pos_name = f"{name}_Pos{pos_count:03d}"
                        if self._mmc.getFocusDevice():
                            list_pos_order.append((pos_name, x_pos, y_pos, z_pos))
                        else:
                            list_pos_order.append(
                                (pos_name, x_pos, y_pos)  # type: ignore
                            )
                        if c < self.scan_size_c - 1:
                            x_pos += increment_x
                        pos_count += 1

            full_pos_list.extend(list_pos_order)

        return full_pos_list

    def set_explorer_dir(self):
        # set the directory
        self.dir = QtW.QFileDialog(self)
        self.dir.setFileMode(QtW.QFileDialog.DirectoryOnly)
        self.save_dir = QtW.QFileDialog.getExistingDirectory(self.dir)
        self.dir_explorer_lineEdit.setText(self.save_dir)
        self.parent_path = Path(self.save_dir)

    def _create_translation_points(self, rows, cols) -> list:

        cam_size_x = self._mmc.getROI(self._mmc.getCameraDevice())[2]
        cam_size_y = self._mmc.getROI(self._mmc.getCameraDevice())[3]
        move_x = cam_size_x - (self.ovelap_spinBox.value() * cam_size_x) / 100
        move_y = cam_size_y - (self.ovelap_spinBox.value() * cam_size_y) / 100
        x = -((cols - 1) * (cam_size_x / 2))
        y = (rows - 1) * (cam_size_y / 2)

        # for 'snake' acquisition
        points = []
        for r in range(rows):
            if r % 2:  # for odd rows
                col = cols - 1
                for c in range(cols):
                    if c == 0:
                        y -= move_y
                    points.append((x, y))
                    if col > 0:
                        col -= 1
                        x -= move_x
            else:  # for even rows
                for c in range(cols):
                    if r > 0 and c == 0:
                        y -= move_y
                    points.append((x, y))
                    if c < cols - 1:
                        x += move_x
        return points

    def _set_translate_point_list(self) -> list:

        if self.display_checkbox.isChecked():
            return []

        t_list = self._create_translation_points(self.scan_size_r, self.scan_size_c)
        if self.stage_tableWidget.rowCount() > 0:
            t_list = t_list * self.stage_tableWidget.rowCount()
        return t_list

    def start_scan(self):

        self.pixel_size = self._mmc.getPixelSizeUm()

        if len(self._mmc.getLoadedDevices()) < 2:
            raise ValueError("Load a cfg file first.")

        if self.pixel_size <= 0:
            raise ValueError("Pixel Size not set.")

        if self.channel_explorer_tableWidget.rowCount() <= 0:
            raise ValueError("Select at least one channel.")

        if self.save_explorer_groupBox.isChecked() and (
            self.fname_explorer_lineEdit.text() == ""
            or (
                self.dir_explorer_lineEdit.text() == ""
                or not Path.is_dir(Path(self.dir_explorer_lineEdit.text()))
            )
        ):
            raise ValueError("select a filename and a valid directory.")

        explore_sample = MDASequence(**self._get_state_dict())

        _mda.SEQUENCE_META[explore_sample] = _mda.SequenceMeta(
            mode="explorer",
            split_channels=True,
            should_save=self.save_explorer_groupBox.isChecked(),
            file_name=self.fname_explorer_lineEdit.text(),
            save_dir=self.dir_explorer_lineEdit.text(),
            explorer_translation_points=self._set_translate_point_list(),
        )

        self._mmc.run_mda(explore_sample)  # run the MDA experiment asynchronously
        return

    def move_to(self):

        if self.pixel_size <= 0:
            raise ValueError("Pixel Size not set.")

        move_to_x = self.x_lineEdit.text()
        move_to_y = self.y_lineEdit.text()

        if move_to_x != "None" and move_to_y != "None":
            move_to_x = float(move_to_x)
            move_to_y = float(move_to_y)
            self._mmc.setXYPosition(move_to_x, move_to_y)
