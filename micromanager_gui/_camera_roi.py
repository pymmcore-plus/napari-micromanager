import warnings

import napari
import napari.viewer
from magicgui import magicgui
from magicgui.widgets import Container
from pymmcore_plus import RemoteMMCore
from qtpy.QtWidgets import QMessageBox


class CameraROI:
    def __init__(self, viewer: napari.viewer.Viewer, mmcore: RemoteMMCore, parent=None):

        self._mmc = mmcore
        self.viewer = viewer
        super().__init__()

        self.w = 10  # for self.center_camera_roi
        self.h = 10  # for self.center_camera_roi

    def general_msg(self, message_1: str, message_2: str):
        msg = QMessageBox()
        msg.setStyleSheet("QLabel {min-width: 280; min-height: 30px;}")
        msg_info_1 = f'<p style="font-size:18pt; color: #4e9a06;">{message_1}</p>'
        msg.setText(msg_info_1)
        msg_info_2 = f'<p style="font-size:15pt; color: #000000;">{message_2}</p>'
        msg.setInformativeText(msg_info_2)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

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

    def camera_roi(self):
        if not self.viewer.layers:
            return

        cam_dev = self._mmc.getCameraDevice()

        max_width = self._mmc.getROI(cam_dev)[2]
        max_height = self._mmc.getROI(cam_dev)[3]

        try:
            shape_layer = self.viewer.layers["Shapes"]

            if len(shape_layer.data) == 0 or len(shape_layer.data) > 1:
                warnings.warn("select one ROI")
                return

            x = int(shape_layer.data[0][0][1])
            y = int(shape_layer.data[0][0][0])
            xsize = int(shape_layer.data[0][1][1] - x)
            ysize = int(shape_layer.data[0][2][0] - y)

            if any(v < 0 for v in [x, y, xsize, ysize]):
                warnings.warn("select a single ROI within the image size")
                return

            cam_dev = self._mmc.getCameraDevice()

            max_width = self._mmc.getROI(cam_dev)[2]
            max_height = self._mmc.getROI(cam_dev)[3]

            if (x + xsize) > max_width or (y + ysize) > max_height:
                warnings.warn("select a single ROI within the image size")
                return

            self._mmc.setROI(cam_dev, x, y, xsize, ysize)

            self.viewer.layers.remove(shape_layer)

            self._mmc.snapImage()
            self.update_viewer(self._mmc.getImage())

        except KeyError:
            message_1 = "Camera ROI"
            message_2 = (
                "Before clicking on the ROI button, "
                'create a "Shapes" layer and draw one ROI'
            )
            self.general_msg(message_1, message_2)

    def crop_roi_size(self, max_height, max_width, w, h):
        return [
            [round(max_height / 2) - round(h / 2), round(max_width / 2) - round(w / 2)],
            [round(max_height / 2) - round(h / 2), round(max_width / 2) + round(w / 2)],
            [round(max_height / 2) + round(h / 2), round(max_width / 2) + round(w / 2)],
            [round(max_height / 2) + round(h / 2), round(max_width / 2) - round(w / 2)],
        ]

    def center_camera_roi(self):
        if not self.viewer.layers:
            return

        c1 = Container(labels=False, layout="horizontal")

        cam_dev = self._mmc.getCameraDevice()

        max_width = self._mmc.getROI(cam_dev)[2]
        max_height = self._mmc.getROI(cam_dev)[3]

        combobox_choices = [
            "Select",
            f"{round(max_width/2)}x{round(max_height/2)}",
            f"{round(max_width/4)}x{round(max_height/4)}",
            f"{round(max_width/6)}x{round(max_height/6)}",
            "Custom",
        ]

        @magicgui(
            auto_call=True,
            layout="horizontal",
            size={"bind": combobox_choices},
            combobox={
                "label": "ComboBox",
                "widget_type": "ComboBox",
                "choices": combobox_choices,
            },
        )
        def cbox(size, combobox):

            if combobox == "Custom":

                try:
                    shape_layer = self.viewer.layers["Shapes"]
                except KeyError:
                    crop_size = self.crop_roi_size(
                        max_height,
                        max_width,
                        round(max_width / 2),
                        round(max_height / 2),
                    )
                    shape_layer = self.viewer.add_shapes(
                        crop_size,
                        name="Shapes",
                        shape_type="rectangle",
                        edge_color="green",
                        opacity=0.5,
                    )

                c = Container(labels=False, layout="horizontal")
                c.width = 495
                c.height = 85

                @magicgui(
                    auto_call=True,
                    layout="horizontal",
                    spinbox_1={
                        "label": "Width",
                        "widget_type": "SpinBox",
                        "max": max_width,
                    },
                )
                def spin_1(spinbox_1=round(max_width / 2)):
                    self.w = spinbox_1
                    crop_size = self.crop_roi_size(
                        max_height, max_width, self.w, self.h
                    )
                    shape_layer.data = crop_size

                c.append(spin_1)

                @magicgui(
                    auto_call=True,
                    layout="horizontal",
                    spinbox_2={
                        "label": "Height",
                        "widget_type": "SpinBox",
                        "max": max_height,
                    },
                )
                def spin_2(spinbox_2=round(max_height / 2)):
                    self.h = spinbox_2
                    crop_size = self.crop_roi_size(
                        max_height, max_width, self.w, self.h
                    )
                    shape_layer.data = crop_size

                c.append(spin_2)

                @magicgui(call_button="OK")
                def btn():
                    x = int(shape_layer.data[0][0][1])
                    y = int(shape_layer.data[0][0][0])
                    xsize = int(shape_layer.data[0][1][1] - x)
                    ysize = int(shape_layer.data[0][2][0] - y)

                    self._mmc.setROI(cam_dev, x, y, xsize, ysize)

                    self.viewer.layers.remove(shape_layer)

                    self._mmc.snapImage()
                    self.update_viewer(self._mmc.getImage())

                    c.hide()

                c.append(btn)
                c.width = 495
                c.height = 85
                c1.hide()
                c.show(run=True)

            else:

                central_max_width = int(combobox.partition("x")[0])
                central_max_height = int(combobox.partition("x")[-1])

                crop_size = self.crop_roi_size(
                    max_height, max_width, central_max_width, central_max_height
                )

                try:
                    shape_layer = self.viewer.layers["Shapes"]
                    shape_layer.data = crop_size
                except KeyError:
                    shape_layer = self.viewer.add_shapes(
                        crop_size,
                        name="Shapes",
                        shape_type="rectangle",
                        edge_color="green",
                        opacity=0.5,
                    )

                if len(c1) == 1:

                    @magicgui(call_button="OK")
                    def btn():
                        x = int(shape_layer.data[0][0][1])
                        y = int(shape_layer.data[0][0][0])
                        xsize = int(shape_layer.data[0][1][1] - x)
                        ysize = int(shape_layer.data[0][2][0] - y)

                        self._mmc.setROI(cam_dev, x, y, xsize, ysize)

                        self.viewer.layers.remove(shape_layer)

                        self._mmc.snapImage()
                        self.update_viewer(self._mmc.getImage())

                        c1.hide()

                    c1.append(btn)
                c1.show(run=True)

        c1.append(cbox)
        c1.show(run=True)

    def camera_full_chip(self):
        self._mmc.clearROI()
        self._mmc.snapImage()
        self.update_viewer(self._mmc.getImage())
