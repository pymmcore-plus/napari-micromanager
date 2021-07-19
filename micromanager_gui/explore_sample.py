from __future__ import annotations

import tempfile
import warnings
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import tifffile
import useq
from qtpy import QtWidgets as QtW
from qtpy import uic
from useq import MDASequence

from ._util import ensure_unique

if TYPE_CHECKING:
    import napari.viewer
    from pymmcore_plus import RemoteMMCore


UI_FILE = str(Path(__file__).parent / "_ui" / "explore_sample.ui")


class ExploreSample(QtW.QWidget):
    # The UI_FILE above contains these objects:
    scan_explorer_groupBox: QtW.QGroupBox
    scan_size_label: QtW.QLabel
    scan_size_spinBox_r: QtW.QSpinBox
    scan_size_spinBox_c: QtW.QSpinBox
    channel_explorer_groupBox: QtW.QGroupBox
    channel_explorer_tableWidget: QtW.QTableWidget
    add_ch_explorer_Button: QtW.QPushButton
    clear_ch_explorer_Button: QtW.QPushButton
    remove_ch_explorer_Button: QtW.QPushButton
    save_explorer_groupBox: QtW.QGroupBox
    dir_explorer_lineEdit: QtW.QLineEdit
    fname_explorer_lineEdit: QtW.QLineEdit
    browse_save_explorer_Button: QtW.QPushButton
    start_scan_Button: QtW.QPushButton
    stop_scan_Button: QtW.QPushButton
    move_to_position_groupBox: QtW.QGroupBox
    move_to_Button: QtW.QPushButton
    x_lineEdit: QtW.QLineEdit
    y_lineEdit: QtW.QLineEdit
    ovelap_spinBox: QtW.QSpinBox

    # metadata associated with a given experiment
    SEQUENCE_META: dict[MDASequence, dict[str, Any]] = {}

    def __init__(self, viewer: napari.viewer.Viewer, mmcore: RemoteMMCore, parent=None):

        self._mmc = mmcore
        self.viewer = viewer
        super().__init__(parent)
        uic.loadUi(UI_FILE, self)

        self.pixel_size = 0

        # connect buttons
        self.add_ch_explorer_Button.clicked.connect(self.add_channel)
        self.remove_ch_explorer_Button.clicked.connect(self.remove_channel)
        self.clear_ch_explorer_Button.clicked.connect(self.clear_channel)

        self.start_scan_Button.clicked.connect(self.start_scan)
        self.move_to_Button.clicked.connect(self.move_to)
        self.browse_save_explorer_Button.clicked.connect(self.set_explorer_dir)

        self.stop_scan_Button.clicked.connect(lambda e: self._mmc.cancel())

        self.x_lineEdit.setText(str(None))
        self.y_lineEdit.setText(str(None))

        # connect mmcore signals
        mmcore.events.systemConfigurationLoaded.connect(self._refresh_channel_list)

        mmcore.events.sequenceStarted.connect(self._on_mda_started)
        mmcore.events.frameReady.connect(self._on_explorer_frame)
        mmcore.events.sequenceFinished.connect(self._on_mda_finished)
        mmcore.events.sequenceFinished.connect(self._refresh_positions)

        @self.viewer.mouse_drag_callbacks.append
        def get_event(viewer, event):
            if self._mmc.getPixelSizeUm() > 0:
                width = self._mmc.getROI(self._mmc.getCameraDevice())[2]
                height = self._mmc.getROI(self._mmc.getCameraDevice())[3]

                x = viewer.cursor.position[-1] * self._mmc.getPixelSizeUm()
                y = viewer.cursor.position[-2] * self._mmc.getPixelSizeUm() * (-1)

                # to match position coordinates with center of the image
                x = x - ((width / 2) * self._mmc.getPixelSizeUm())
                y = y - ((height / 2) * self._mmc.getPixelSizeUm() * (-1))

            else:
                x, y = None, None

            self.x_lineEdit.setText(f"{x:.1f}")
            self.y_lineEdit.setText(f"{y:.1f}")

    def _on_mda_started(self, sequence: useq.MDASequence):
        """ "create temp folder and block gui when mda starts."""
        self.viewer.grid.enabled = False
        self.temp_folder = tempfile.TemporaryDirectory(None, str(sequence.uid))
        self._set_enabled(False)

    def _on_explorer_frame(self, image: np.ndarray, event: useq.MDAEvent):
        seq = event.sequence
        meta = self.SEQUENCE_META.get(seq, {})

        if meta.get("mode") == "explorer":

            pos_idx = event.index["p"]

            image_name = f'{event.channel.config}_idx{event.index["c"]}.tif'

            x = event.x_pos / self.pixel_size
            y = event.y_pos / self.pixel_size * (-1)

            file_name = meta.get("file_name") if meta.get("save_group") else "Exp"

            layer_name = (
                f"Pos{pos_idx:03d}_{file_name}_[{event.channel.config}_idx"
                f"{event.index['c']}]_{datetime.now().strftime('%H:%M:%S:%f')}"
            )

            layer = self.viewer.add_image(
                image, name=layer_name, opacity=0.5, translate=(y, x)
            )

            self.viewer.reset_view()

            # add metadata to layer
            layer.metadata["useq_sequence"] = seq
            layer.metadata["uid"] = seq.uid
            layer.metadata["scan_coord"] = (y, x)
            layer.metadata["scan_position"] = f"Pos{pos_idx:03d}"
            layer.metadata["ch_name"] = f"{event.channel.config}"
            layer.metadata["ch_id"] = f'{event.index["c"]}'

            image_name = (
                f'Pos{pos_idx:03d}_{event.channel.config}_idx{event.index["c"]}.tif'
            )

            # save first image in the temp folder
            if hasattr(self, "temp_folder"):
                savefile = Path(self.temp_folder.name) / image_name
                tifffile.imsave(str(savefile), image, imagej=True)

    def _on_mda_finished(self, sequence: useq.MDASequence):
        meta = self.SEQUENCE_META.get(sequence, {})

        if meta.get("mode") == "explorer":

            if meta.get("save_group"):
                self._save_explorer_scan(sequence, meta)

            if hasattr(self, "temp_folder"):
                self.temp_folder.cleanup()

            self.SEQUENCE_META.pop(sequence)
        self._set_enabled(True)

    def _save_explorer_scan(self, sequence, meta):

        print(len(sequence.channels))

        path = Path(meta.get("save_dir"))
        file_name = f'scan_{meta.get("file_name")}'

        folder_name = ensure_unique(path / file_name, extension="", ndigits=3)
        folder_name.mkdir(parents=True, exist_ok=True)

        width = self._mmc.getROI(self._mmc.getCameraDevice())[2]
        height = self._mmc.getROI(self._mmc.getCameraDevice())[3]

        for cn in range(len(sequence.channels)):

            scan_stack = np.empty((1, height, width))

            for i in self.viewer.layers:

                if i.metadata.get("uid") == sequence.uid and int(cn) == int(
                    i.metadata.get("ch_id")
                ):

                    ch_name = i.metadata.get("ch_name")

                    i.data = i.data[np.newaxis, ...]

                    if i.metadata.get("scan_position") == "Pos000":
                        scan_stack = i.data
                    else:
                        scan_stack = np.concatenate((scan_stack, i.data))

            if scan_stack.shape[0] > 1:

                tifffile.imsave(
                    str(folder_name / f"{folder_name.stem}_" f"{ch_name}.tif"),
                    scan_stack.astype("uint16"),
                    imagej=True,
                )

    def _set_enabled(self, enabled):
        self.scan_size_spinBox_r.setEnabled(enabled)
        self.scan_size_spinBox_c.setEnabled(enabled)
        self.ovelap_spinBox.setEnabled(enabled)
        self.channel_explorer_groupBox.setEnabled(enabled)
        self.move_to_Button.setEnabled(enabled)
        self.start_scan_Button.setEnabled(enabled)
        self.save_explorer_groupBox.setEnabled(enabled)

    def _refresh_channel_list(self):
        self.clear_channel()

    def _refresh_positions(self):
        if self._mmc.getXYStageDevice():
            x, y = self._mmc.getXPosition(), self._mmc.getYPosition()
        else:
            x, y = None, None

        self.x_lineEdit.setText(f"{x:.1f}")
        self.y_lineEdit.setText(f"{y:.1f}")

    # add, remove, clear channel table
    def add_channel(self):
        dev_loaded = list(self._mmc.getLoadedDevices())
        if len(dev_loaded) > 1:

            idx = self.channel_explorer_tableWidget.rowCount()
            self.channel_explorer_tableWidget.insertRow(idx)

            # create a combo_box for channels in the table
            self.channel_explorer_comboBox = QtW.QComboBox(self)
            self.channel_explorer_exp_spinBox = QtW.QSpinBox(self)
            self.channel_explorer_exp_spinBox.setRange(0, 10000)
            self.channel_explorer_exp_spinBox.setValue(100)

            if "Channel" not in self._mmc.getAvailableConfigGroups():
                raise ValueError("Could not find 'Channel' in the ConfigGroups")
            channel_list = list(self._mmc.getAvailableConfigs("Channel"))
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

    def _get_state_dict(self) -> dict:
        state = {
            "axis_order": "tpzc",
            "channels": [],
            "stage_positions": [],
            "z_plan": None,
            "time_plan": None,
        }
        state["channels"] = [
            {
                "config": self.channel_explorer_tableWidget.cellWidget(
                    c, 0
                ).currentText(),
                "group": self._mmc.getChannelGroup() or "Channel",
                "exposure": self.channel_explorer_tableWidget.cellWidget(c, 1).value(),
            }
            for c in range(self.channel_explorer_tableWidget.rowCount())
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

        # get current position
        x_curr_pos_explorer = float(self._mmc.getXPosition())
        y_curr_pos_explorer = float(self._mmc.getYPosition())
        z_curr_pos_explorer = float(self._mmc.getZPosition())

        # calculate initial scan position
        width = self._mmc.getROI(self._mmc.getCameraDevice())[2]
        height = self._mmc.getROI(self._mmc.getCameraDevice())[3]

        overlap_percentage = self.ovelap_spinBox.value()
        overlap_px_w = width - (width * overlap_percentage) / 100
        overlap_px_h = height - (height * overlap_percentage) / 100

        if self.scan_size_r == 1 and self.scan_size_c == 1:
            raise Exception("RxC -> 1x1. Use MDA to acquire a single position image.")

        move_x = (
            ((width / 2) * (self.scan_size_c - 1)) - overlap_px_w
        ) * self.pixel_size

        move_y = (
            ((height / 2) * (self.scan_size_r - 1)) - overlap_px_h
        ) * self.pixel_size

        x_pos_explorer = x_curr_pos_explorer - move_x
        y_pos_explorer = y_curr_pos_explorer + move_y

        # to match position coordinates with center of the image
        x_pos_explorer = x_pos_explorer - ((width) * self.pixel_size)
        y_pos_explorer = y_pos_explorer - ((height) * self.pixel_size * (-1))

        # calculate position increments depending on pixle size
        if overlap_percentage > 0:
            increment_x = overlap_px_w * self.pixel_size
            increment_y = overlap_px_h * self.pixel_size
        else:
            increment_x = width * self.pixel_size
            increment_y = height * self.pixel_size

        return self.create_pos_grid_coordinates(
            z_curr_pos_explorer,
            x_pos_explorer,
            y_pos_explorer,
            increment_x,
            increment_y,
        )

    def create_pos_grid_coordinates(
        self,
        z_curr_pos_explorer,
        x_pos_explorer,
        y_pos_explorer,
        increment_x,
        increment_y,
    ):
        list_pos_order = []
        for r in range(self.scan_size_r):
            if r == 0 or (r % 2) == 0:
                for c in range(self.scan_size_c):  # for even rows
                    if r > 0 and c == 0:
                        y_pos_explorer = y_pos_explorer - increment_y
                    list_pos_order.append(
                        [x_pos_explorer, y_pos_explorer, z_curr_pos_explorer]
                    )
                    if c < self.scan_size_c - 1:
                        x_pos_explorer = x_pos_explorer + increment_x
            else:  # for odd rows
                col = self.scan_size_c - 1
                for c in range(self.scan_size_c):
                    if c == 0:
                        y_pos_explorer = y_pos_explorer - increment_y
                    list_pos_order.append(
                        [x_pos_explorer, y_pos_explorer, z_curr_pos_explorer]
                    )
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

        self.pixel_size = self._mmc.getPixelSizeUm()

        if len(self._mmc.getLoadedDevices()) < 2:
            raise ValueError("Load a cfg file first.")

        if self.pixel_size <= 0:
            raise ValueError("PIXEL SIZE NOT SET.")

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

        self.SEQUENCE_META[explore_sample] = {
            "mode": "explorer",
            "split_channels": True,
            "save_group": self.save_explorer_groupBox.isChecked(),
            "file_name": self.fname_explorer_lineEdit.text(),
            "save_dir": self.dir_explorer_lineEdit.text(),
        }
        self._mmc.run_mda(explore_sample)  # run the MDA experiment asynchronously
        return

    def move_to(self):

        move_to_x = self.x_lineEdit.text()
        move_to_y = self.y_lineEdit.text()

        if move_to_x == "None" and move_to_y == "None":
            warnings.warn("PIXEL SIZE NOT SET.")
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
