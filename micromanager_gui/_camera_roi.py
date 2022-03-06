from __future__ import annotations

import math
import warnings
from typing import TYPE_CHECKING

import napari
import napari.viewer
from qtpy import QtWidgets as QtW

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus, RemoteMMCore

CAM_ROI_LAYER = "Camera_ROI"


class CameraROI:
    def __init__(
        self,
        viewer: napari.viewer.Viewer,
        mmcore: CMMCorePlus or RemoteMMCore,
        combobox: QtW.QComboBox,
        push_btn: QtW.QPushButton,
    ):

        self._mmc = mmcore

        self.viewer = viewer
        super().__init__()

        self.camera_roi_cbox = combobox
        self.camera_roi_cbox.clear()
        self.camera_roi_cbox.addItems(["Full", "ROI", "1/4", "1/16", "1/64"])

        self.crop_button = push_btn
        self.crop_button.setEnabled(False)
        self.crop_button.clicked.connect(self._on_crop_pushed)
        self.camera_roi_cbox.currentTextChanged.connect(self._on_roi_cbox_change)

    def update_viewer(self):
        self._mmc.snapImage()
        data = self._mmc.getImage()

        if data is None:
            try:
                data = self._mmc.getLastImage()
            except (RuntimeError, IndexError):
                # circular buffer empty
                return
        try:
            preview_layer = self.viewer.layers["preview"]
            preview_layer.data = data
        except KeyError:
            preview_layer = self.viewer.add_image(data, name="preview")

        self.viewer.reset_view()

    def clear_roi_and_snap(self):
        self._mmc.clearROI()
        self.update_viewer()

    def get_camera_and_size(self):
        return self._mmc.getROI(self._mmc.getCameraDevice())[-2:]

    def center_crop_roi_size(self, max_height, max_width, w, h):
        return [
            [(max_height // 2) - (h // 2), (max_width // 2) - (w // 2)],
            [(max_height // 2) - (h // 2), (max_width // 2) + (w // 2)],
            [(max_height // 2) + (h // 2), (max_width // 2) + (w // 2)],
            [(max_height // 2) + (h // 2), (max_width // 2) - (w // 2)],
        ]

    def add_roi_layer(self):
        return self.viewer.add_shapes(
            name=CAM_ROI_LAYER,
            shape_type="rectangle",
            edge_color="green",
            opacity=0.5,
        )

    def make_rectangle_roi_layer(self):
        cam_roi_layer = self.add_roi_layer()
        cam_roi_layer.mode = "ADD_RECTANGLE"

    def _on_roi_cbox_change(self, mode: str):
        self.crop_button.setEnabled(mode != "Full")
        if mode == "Full":
            for lay in self.viewer.layers:
                if lay.name == CAM_ROI_LAYER:
                    self.viewer.layers.remove(lay)
            self.clear_roi_and_snap()
        elif mode == "ROI":
            self.camera_custom_crop()
        else:
            self.camera_centered_crop()

    def camera_centered_crop(self):
        self.clear_roi_and_snap()

        max_width, max_height = self.get_camera_and_size()

        item = self.camera_roi_cbox.currentText()
        _size = math.sqrt(int(item.partition("/")[-1]))

        crop_size = self.center_crop_roi_size(
            max_height, max_width, max_height // _size, max_height // _size
        )

        try:
            cam_roi_layer = self.viewer.layers[CAM_ROI_LAYER]
            cam_roi_layer.data = crop_size
            cam_roi_layer.mode = "select"
        except KeyError:
            cam_roi_layer = self.add_roi_layer()
            cam_roi_layer.data = crop_size
            cam_roi_layer.mode = "select"

    def camera_custom_crop(self):
        try:
            cam_roi_layer = self.viewer.layers[CAM_ROI_LAYER]
            if cam_roi_layer.nshapes == 0:
                cam_roi_layer.mode = "ADD_RECTANGLE"
            else:
                cam_roi_layer.mode = "select"
        except KeyError:
            self.make_rectangle_roi_layer()

    def _on_crop_pushed(self):
        try:
            cam_roi_layer = self.viewer.layers[CAM_ROI_LAYER]
            self.crop(cam_roi_layer)
        except KeyError:
            self.make_rectangle_roi_layer()

    def crop(self, cam_roi_layer):

        shape_selected_list = list(cam_roi_layer.selected_data)

        shape_selected_idx = 0 if not shape_selected_list else shape_selected_list[0]

        x = int(cam_roi_layer.data[shape_selected_idx][0][1])
        y = int(cam_roi_layer.data[shape_selected_idx][0][0])
        xsize = int(cam_roi_layer.data[shape_selected_idx][1][1] - x)
        ysize = int(cam_roi_layer.data[shape_selected_idx][2][0] - y)

        if any(v < 0 for v in [x, y, xsize, ysize]):
            warnings.warn("select a ROI within the image size")
            return

        max_width, max_height = self.get_camera_and_size()
        if (x + xsize) > max_width or (y + ysize) > max_height:
            warnings.warn("select a ROI within the image size")
            return

        self._mmc.setROI(x, y, xsize, ysize)

        self.viewer.layers.remove(cam_roi_layer)
        self.update_viewer()
