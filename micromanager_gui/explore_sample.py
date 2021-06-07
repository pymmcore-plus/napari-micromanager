from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

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


    def __init__(self, mmcore, parent=None):
            self._mmc = mmcore
            super().__init__(parent)  
            uic.loadUi(UI_FILE, self)

            self.start_scan_Button.clicked.connect(self.start_scan)
    
    def enable_explorer_groupbox(self):
        self.scan_size_spinBox_r.setEnabled(True)
        self.scan_size_spinBox_c.setEnabled(True)
        self.scan_channel_comboBox.setEnabled(True)
        self.scan_exp_spinBox.setEnabled(True)
        self.move_to_Button.setEnabled(True)
        self.start_scan_Button.setEnabled(True)

    def disable_explorer_groupbox(self):
        self.scan_size_spinBox_r.setEnabled(False)
        self.scan_size_spinBox_c.setEnabled(False)
        self.scan_channel_comboBox.setEnabled(False)
        self.scan_exp_spinBox.setEnabled(False)
        self.move_to_Button.setEnabled(False)
        self.start_scan_Button.setEnabled(False)

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

        print(state)
        return state

    
    def set_grid(self):

        #TODO: add % overlap 

        self.scan_size_r = self.scan_size_spinBox_r.value()
        self.scan_size_c = self.scan_size_spinBox_c.value()

        """get current position"""
        x_curr_pos_explorer = float(self._mmc.getXPosition())
        y_curr_pos_explorer = float(self._mmc.getYPosition())
        z_curr_pos_explorer = float(self._mmc.getZPosition())

        """calculate initial scan position"""
        width = self._mmc.getROI(self._mmc.getCameraDevice())[2]  # maybe they are inverted
        height = self._mmc.getROI(self._mmc.getCameraDevice())[3]  # maybe they are inverted

        move_x = (width / 2) * (self.scan_size_r - 1) * self._mmc.getPixelSizeUm()
        move_y = (height / 2) * (self.scan_size_c - 1) * self._mmc.getPixelSizeUm()

        x_pos_explorer = x_curr_pos_explorer - move_x
        y_pos_explorer = y_curr_pos_explorer + move_y

        """calculate position increments depending on pixle size"""
        increment_x = width * self._mmc.getPixelSizeUm()
        increment_y = height * self._mmc.getPixelSizeUm()

        list_pos_order  = []

        """create the xyz position matrix"""
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

        print(list_pos_order)
        return list_pos_order
        
        
    def start_scan(self):
        explore_sample = MDASequence(**self._get_state_dict())
        self._mmc.run_mda(explore_sample)  # run the MDA experiment asynchronously
        return


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication

    app = QApplication([])
    window = ExploreSample()
    window.show()
    app.exec_()







#     def move_to(self):

#         string_coord_x = self.x_lineEdit.text()
#         string_coord_y = self.y_lineEdit.text()

#         if not string_coord_x == "None" and not string_coord_y == "None":

#             coord_x = float(string_coord_x)
#             coord_y = float(string_coord_y)
#             # print(f'COORDS: {coord_x},{coord_y}')

#             x_snap = self.shape_stitched_x / self.scan_size_c
#             y_snap = self.shape_stitched_y / self.scan_size_r
#             # print(x_snap, y_snap)

#             x_snap_increment = x_snap
#             y_snap_increment = y_snap

#             done = False
#             col = 0
#             for _ in range(self.total_size):

#                 if done:
#                     break

#                 if coord_x <= x_snap:
#                     # for row in range(self.scan_size):
#                     for row in range(self.scan_size_r):
#                         if coord_y <= y_snap:
#                             # print(f'coord_x = {coord_x}, coord_y = {coord_y}')
#                             # print(f'row = {row}, col = {col}')
#                             x_scan_pos = self.array_pos_x[row][col]
#                             y_scan_pos = self.array_pos_y[row][col]
#                             z_scan_pos = self.array_pos_z[row][col]
#                             # print(f'moving to x: {x_scan_pos}')
#                             # print(f'moving to y: {y_scan_pos}')
#                             # print(f'moving to z: {z_scan_pos}')
#                             # set position
#                             self._mmc.setXYPosition(x_scan_pos, y_scan_pos)
#                             self._mmc.setPosition("Z_Stage", z_scan_pos)

#                             # snap image at position
#                             self._mmc.setExposure(int(self.scan_exp_spinBox.value()))
#                             self._mmc.setConfig(
#                                 "Channel", self.scan_channel_comboBox.currentText()
#                             )
#                             self._mmc.snapImage()
#                             image = self._mmc.getImage()
#                             self.new_frame.emit("preview", image)
#                             done = True
#                             break

#                         else:
#                             y_snap = y_snap + y_snap_increment
#                 else:
#                     x_snap = x_snap + x_snap_increment
#                     col += 1


# # removed from main_window
# # def get_explorer_info(self, shape_stitched_x, shape_stitched_y):

# #     # Get coordinates mouse_drag_callbacks
# #     @self.viewer.mouse_drag_callbacks.append  # is it possible to double click?
# #     def get_event_add(viewer, event):
# #         try:
# #             for i in self.viewer.layers:
# #                 selected_layer = self.viewer.layers.selected
# #                 if "stitched_" in str(i) and "stitched_" in str(selected_layer):
# #                     layer = self.viewer.layers[str(i)]
# #                     coord = layer.coordinates
# #                     # print(f'\ncoordinates: x={coord[1]}, y={coord[0]}')
# #                     coord_x = coord[1]
# #                     coord_y = coord[0]
# #                     if coord_x <= shape_stitched_x and coord_y < shape_stitched_y:
# #                         if coord_x > 0 and coord_y > 0:
# #                             self.explorer.x_lineEdit.setText(str(round(coord_x)))
# #                             self.explorer.y_lineEdit.setText(str(round(coord_y)))
# #                             break

# #                         else:
# #                             self.explorer.x_lineEdit.setText("None")
# #                             self.explorer.y_lineEdit.setText("None")
# #                     else:
# #                         self.explorer.x_lineEdit.setText("None")
# #                         self.explorer.y_lineEdit.setText("None")
# #         except KeyError:
# #             pass


# array(  [
#             [0., 0.],[0., 0.]
#         ]
#     )


# array(  [
#             [
#                 [0., 0., 0.], [0., 0., 0.]
#             ],

#             [
#                 [0., 0., 0.],[0., 0., 0.]
#             ]
#         ]
#     )

# array(  [
#             [
#                 [0., 0.],[0., 0.]
#             ],

#             [
#                 [0., 0.],[0., 0.]
#             ],

#             [
#                 [0., 0.],[0., 0.]
#             ]
#         ]
#       )


