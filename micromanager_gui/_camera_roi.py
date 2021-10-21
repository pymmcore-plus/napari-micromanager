import math
import warnings

import napari
import napari.viewer
from pymmcore_plus import RemoteMMCore
from qtpy import QtWidgets as QtW


class CameraROI:
    def __init__(
        self,
        viewer: napari.viewer.Viewer,
        mmcore: RemoteMMCore,
        combobox: QtW.QComboBox,
        push_btn: QtW.QPushButton,
        parent=None,
    ):

        self._mmc = mmcore

        self.viewer = viewer
        super().__init__()

        self.camera_roi_cbox = combobox
        self.camera_roi_cbox.addItems(["Full", "ROI", "1/4", "1/16", "1/64"])

        self.crop_button = push_btn
        self.crop_button.setEnabled(False)
        self.crop_button.clicked.connect(self.crop_camera)
        self.camera_roi_cbox.currentIndexChanged.connect(self.roi_action)

    def update_viewer(self, data=None):
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
        self._mmc.snapImage()
        self.update_viewer(self._mmc.getImage())

    def get_camera_and_size(self):
        cam_dev = self._mmc.getCameraDevice()
        max_width = self._mmc.getROI(cam_dev)[2]
        max_height = self._mmc.getROI(cam_dev)[3]
        return max_width, max_height

    def center_crop_roi_size(self, max_height, max_width, w, h):
        return [
            [(max_height // 2) - (h // 2), (max_width // 2) - (w // 2)],
            [(max_height // 2) - (h // 2), (max_width // 2) + (w // 2)],
            [(max_height // 2) + (h // 2), (max_width // 2) + (w // 2)],
            [(max_height // 2) + (h // 2), (max_width // 2) - (w // 2)],
        ]

    def roi_action(self):

        if self.camera_roi_cbox.currentText() == "Full":
            self.crop_button.setEnabled(False)
            self.camera_full_chip()

        if self.camera_roi_cbox.currentText() == "ROI":
            self.crop_button.setEnabled(True)
            self.camera_custom_crop()

        if self.camera_roi_cbox.currentIndex() > 1:
            self.crop_button.setEnabled(True)
            self.camera_centered_crop(self.camera_roi_cbox.currentText())

    def camera_full_chip(self):
        for lay in self.viewer.layers:
            if lay.name == "Camera_ROI":
                self.viewer.layers.remove(lay)
        self.clear_roi_and_snap()
        self.crop_button.setEnabled(False)

    def camera_centered_crop(self, choice):
        self.clear_roi_and_snap()

        max_width, max_height = self.get_camera_and_size()

        item = self.camera_roi_cbox.currentText()
        _size = math.sqrt(int(item.partition("/")[-1]))

        crop_size = self.center_crop_roi_size(
            max_height, max_width, max_height // _size, max_height // _size
        )

        try:
            cam_roi_layer = self.viewer.layers["Camera_ROI"]
            cam_roi_layer.data = crop_size
            cam_roi_layer.mode = "select"
        except KeyError:
            cam_roi_layer = self.viewer.add_shapes(
                crop_size,
                name="Camera_ROI",
                shape_type="rectangle",
                edge_color="green",
                opacity=0.5,
            )
            cam_roi_layer.mode = "select"

    def camera_custom_crop(self):
        try:
            cam_roi_layer = self.viewer.layers["Camera_ROI"]
            if cam_roi_layer.nshapes == 0:
                cam_roi_layer.mode = "ADD_RECTANGLE"
            else:
                cam_roi_layer.mode = "select"
        except KeyError:
            cam_roi_layer = self.viewer.add_shapes(
                name="Camera_ROI",
                shape_type="rectangle",
                edge_color="green",
                opacity=0.5,
            )
            cam_roi_layer.mode = "ADD_RECTANGLE"

    def crop_camera(self):
        try:
            cam_roi_layer = self.viewer.layers["Camera_ROI"]

            shape_selected_list = list(cam_roi_layer.selected_data)

            shape_selected_idx = (
                0 if not shape_selected_list else shape_selected_list[0]
            )

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
            self._mmc.snapImage()
            self.update_viewer(self._mmc.getImage())

        except KeyError:

            cam_roi_layer = self.viewer.add_shapes(
                name="Camera_ROI",
                shape_type="rectangle",
                edge_color="green",
                opacity=0.5,
            )
            cam_roi_layer.mode = "ADD_RECTANGLE"

        except IndexError:
            warnings.warn("select a ROI within the image size")
