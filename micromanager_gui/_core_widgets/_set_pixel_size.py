import itertools
import re
from typing import Optional

from pymmcore_plus import CMMCorePlus
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt

from micromanager_gui._core import get_core_singleton
from micromanager_gui._gui_objects._objective_widget import MMObjectivesWidget

RESOLUTION_ID_PREFIX = "px_size_"


class PixelSizeTable(QtW.QTableWidget):
    """Create a Table to set pixel size configurations"""

    def __init__(
        self,
        mmcore: Optional[CMMCorePlus] = None,
        objective_device: Optional[str] = None,
    ):
        super().__init__()

        self._mmc = mmcore or get_core_singleton()

        self._mmc.loadSystemConfiguration()  # just to test, to remove later

        self._objective_device = (
            objective_device or MMObjectivesWidget()._guess_objective_device()
        )

        self.setMinimumWidth(570)
        hdr = self.horizontalHeader()
        hdr.setSectionResizeMode(hdr.Stretch)
        hdr.setDefaultAlignment(Qt.AlignHCenter)
        vh = self.verticalHeader()
        vh.setVisible(False)
        vh.setSectionResizeMode(vh.ResizeMode.Fixed)
        self.setSelectionBehavior(QtW.QAbstractItemView.SelectItems)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(
            [
                "Objective",
                "Magnification",
                "Camera Pixel Size (µm)",
                "Image Pixel Size (µm)",
            ]
        )

    def _on_camera_px_size_changed(self, value: float):
        row = self.camera_px_size.property("row")
        wdg = self.cellWidget(row, 3)  # image_px_size
        wdg.setValue(value / self.mag.value())

    def _on_image_px_size_changed(self, value: float):
        row = self.image_px_size.property("row")
        wdg = self.cellWidget(row, 2)  # camera_px_size
        wdg.setValue(value * self.mag.value())

    def _on_mag_changed(self):
        row = self.mag.property("row")
        cam_wdg = self.cellWidget(row, 2)  # camera_px_size
        img_wdg = self.cellWidget(row, 3)  # image_px_size
        self._on_camera_px_size_changed(cam_wdg.value())
        self._on_image_px_size_changed(img_wdg.value())

    def _on_obj_combobox_changed(self, obj_label: str):

        row = self.objective_combo.property("row")
        mag_wdg = self.cellWidget(row, 1)  # mag
        cam_wdg = self.cellWidget(row, 2)  # camera_px_size
        img_wdg = self.cellWidget(row, 3)  # image_px_size

        if match := re.search(r"(\d{1,3})[xX]", obj_label):
            mag_wdg.setValue(int(match.groups()[0]))
        else:
            mag_wdg.setValue(1)
        self._on_camera_px_size_changed(cam_wdg.value())
        self._on_image_px_size_changed(img_wdg.value())

    def _add_to_table(self, row: int):

        self.camera_px_size = self._make_spinbox()
        self.camera_px_size.setProperty("row", row)
        self.camera_px_size.valueChanged.connect(self._on_camera_px_size_changed)
        self.image_px_size = self._make_spinbox()
        self.image_px_size.setProperty("row", row)
        self.image_px_size.setDecimals(4)
        self.image_px_size.valueChanged.connect(self._on_image_px_size_changed)

        self.mag = QtW.QSpinBox()
        self.mag.setProperty("row", row)
        self.mag.setAlignment(Qt.AlignCenter)
        self.mag.setMinimum(1)
        self.mag.setValue(10)
        self.mag.setMaximum(1000)
        self.mag.valueChanged.connect(self._on_mag_changed)

        self.objective_combo = QtW.QComboBox()
        self.objective_combo.setProperty("row", row)
        self.objective_labels = self._mmc.getStateLabels(self._objective_device)
        self.objective_combo.addItems(self.objective_labels)
        self.objective_combo.currentTextChanged.connect(self._on_obj_combobox_changed)
        self.objective_combo.setCurrentIndex(0)

        self.a = self.setCellWidget(row, 0, self.objective_combo)
        self.setCellWidget(row, 1, self.mag)
        self.setCellWidget(row, 2, self.camera_px_size)
        self.setCellWidget(row, 3, self.image_px_size)

    def _set_mm_pixel_size(self):
        for r in range(self.rowCount()):
            obj_label = self.cellWidget(r, 0).currentText()
            px_size_um = self.cellWidget(r, 3).value()
            mag = self.cellWidget(r, 1).value()

            if not px_size_um:
                return

            resolutionID = f"{RESOLUTION_ID_PREFIX}{mag}x"

            if self._mmc.getAvailablePixelSizeConfigs():
                #  remove px cfg if contains obj_label in ConfigData
                for cfg in self._mmc.getAvailablePixelSizeConfigs():
                    cfg_data = list(
                        itertools.chain(*self._mmc.getPixelSizeConfigData(cfg))
                    )
                    if obj_label in cfg_data:
                        self._mmc.deletePixelSizeConfig(cfg)

            if resolutionID in self._mmc.getAvailablePixelSizeConfigs():
                self._mmc.deletePixelSizeConfig(resolutionID)

            self._mmc.definePixelSizeConfig(
                resolutionID, self._objective_device, "Label", obj_label
            )
            self._mmc.setPixelSizeUm(resolutionID, px_size_um)

            # to remove print
            print(f"new pixel configuration:{resolutionID} -> pixel size: {px_size_um}")

            self.parent().parent().close()

    def _make_spinbox(self):
        spin = QtW.QDoubleSpinBox()
        spin.setAlignment(Qt.AlignCenter)
        spin.setMinimum(0.0)
        spin.setMaximum(1000.0)
        spin.setValue(0.0)
        return spin


class PixelSizeWidget(QtW.QWidget):
    """Make a widget to set the pixel size configuration"""

    def __init__(self) -> None:
        super().__init__()

        self.table = PixelSizeTable()

        main_layout = QtW.QVBoxLayout()

        self.buttons = QtW.QWidget()
        buttons_layout = QtW.QHBoxLayout()
        self.new_row_button = QtW.QPushButton(text="New Row")
        self.delete_row_button = QtW.QPushButton(text="Delete Row")
        self.set_button = QtW.QPushButton(text="Set")
        self.new_row_button.clicked.connect(self._insert_new_row)
        self.delete_row_button.clicked.connect(self._delete_selected_row)
        self.set_button.clicked.connect(self.table._set_mm_pixel_size)
        buttons_layout.addWidget(self.new_row_button)
        buttons_layout.addWidget(self.delete_row_button)
        buttons_layout.addWidget(self.set_button)
        self.buttons.setLayout(buttons_layout)

        main_layout.addWidget(self.table)
        main_layout.addWidget(self.buttons)

        main_wdg = QtW.QWidget()
        main_wdg.setLayout(main_layout)

        self.setLayout(QtW.QHBoxLayout())
        self.layout().addWidget(main_wdg)

    def _insert_new_row(self):
        if not self.table._objective_device:
            return
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table._add_to_table(row)

    def _delete_selected_row(self):
        selected_row = [r.row() for r in self.table.selectedIndexes()]
        if not selected_row or len(selected_row) > 1:
            return
        self.table.removeRow(selected_row[0])


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = PixelSizeWidget()
    win.show()
    sys.exit(app.exec_())
