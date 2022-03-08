import itertools
from typing import Optional

from pymmcore_plus import CMMCorePlus
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt
from superqt.utils import signals_blocked

from .._core import get_core_singleton
from .._gui_objects._objective_widget import MMObjectivesWidget

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
                "Objective Magnification",
                "Camera Pixel Size (µm)",
                "Image Pixel Size (µm)",
            ]
        )

        if self._mmc.getAvailablePixelSizeConfigs():
            self._add_px_cfg_to_table(self.rowCount())

    def _on_camera_px_size_changed(self, value: float):
        row = self.sender().property("row")
        mag = self.cellWidget(row, 1)  # mag
        img_wdg = self.cellWidget(row, 3)  # image_px_size
        with signals_blocked(img_wdg):
            img_wdg.setValue(value / (mag.value() * self._mmc.getMagnificationFactor()))

    def _on_image_px_size_changed(self, value: float):
        row = self.sender().property("row")
        mag = self.cellWidget(row, 1)  # mag
        cam_wdg = self.cellWidget(row, 2)  # camera_px_size
        with signals_blocked(cam_wdg):
            cam_wdg.setValue(value * mag.value())

    def _on_mag_changed(self, x: int):
        row = self.sender().property("row")
        cam_wdg = self.cellWidget(row, 2)  # camera_px_size
        img_wdg = self.cellWidget(row, 3)  # image_px_size
        with signals_blocked(img_wdg):
            img_wdg.setValue(cam_wdg.value() / (x * self._mmc.getMagnificationFactor()))

    def _disconnect(self, row):
        mag_wdg = self.cellWidget(row, 1)
        cam_px_wdg = self.cellWidget(row, 2)
        img_px_wdg = self.cellWidget(row, 3)
        mag_wdg.valueChanged.disconnect(self._on_mag_changed)
        cam_px_wdg.valueChanged.disconnect(self._on_camera_px_size_changed)
        img_px_wdg.valueChanged.disconnect(self._on_image_px_size_changed)

    def _create_widgets(self, row):
        self.objective_combo = QtW.QComboBox()
        self.objective_combo.setProperty("row", row)
        self.objective_labels = self._mmc.getStateLabels(self._objective_device)
        self.objective_combo.addItems(self.objective_labels)

        self.mag = QtW.QSpinBox()
        self.mag.setProperty("row", row)
        self.mag.setAlignment(Qt.AlignCenter)
        self.mag.setMinimum(1)
        self.mag.setMaximum(1000)
        self.mag.valueChanged.connect(self._on_mag_changed)

        self.camera_px_size = self._make_double_spinbox(row)
        self.camera_px_size.valueChanged.connect(self._on_camera_px_size_changed)

        self.image_px_size = self._make_double_spinbox(row)
        self.image_px_size.valueChanged.connect(self._on_image_px_size_changed)

        return [self.objective_combo, self.mag, self.camera_px_size, self.image_px_size]

    def _make_double_spinbox(self, row):
        spin = QtW.QDoubleSpinBox()
        spin.setAlignment(Qt.AlignCenter)
        spin.setDecimals(4)
        spin.setMinimum(0.0000)
        spin.setMaximum(1000.0000)
        spin.setValue(0.0)
        spin.setProperty("row", row)
        return spin

    def _add_row(self, row, items: list):
        self.setCellWidget(row, 0, items[0])
        self.setCellWidget(row, 1, items[1])
        self.setCellWidget(row, 2, items[2])
        self.setCellWidget(row, 3, items[3])

    def _get_px_cfg_and_objective(self) -> list:

        cfg_obj = []
        objective_labels = self._mmc.getStateLabels(self._objective_device)

        for cfg in self._mmc.getAvailablePixelSizeConfigs():
            cfg_data = list(itertools.chain(*self._mmc.getPixelSizeConfigData(cfg)))

            c_o = [(o, cfg) for o in objective_labels if o in cfg_data]

            cfg_obj.append(c_o[0])

        return cfg_obj

    def _add_to_table(self, row: int):
        wdg_list = self._create_widgets(row)
        self._add_row(row, wdg_list)

    def _add_px_cfg_to_table(self, row):
        items = self._get_px_cfg_and_objective()
        for obj, cfg in items:
            wdg_list = self._create_widgets(row)
            self.insertRow(row)
            self._add_row(row, wdg_list)
            self.objective_combo.setCurrentText(obj)
            self.image_px_size.setValue(self._mmc.getPixelSizeUmByID(cfg))
            row += 1

    def _set_mm_pixel_size(self):

        for r in range(self.rowCount()):
            obj_label = self.cellWidget(r, 0).currentText()
            px_size_um = float(self.cellWidget(r, 3).text())
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
                        break

            if resolutionID in self._mmc.getAvailablePixelSizeConfigs():
                self._mmc.deletePixelSizeConfig(resolutionID)

            self._mmc.definePixelSizeConfig(
                resolutionID, self._objective_device, "Label", obj_label
            )
            self._mmc.setPixelSizeUm(resolutionID, px_size_um)

            self.parent().parent().close()


class PixelSizeWidget(QtW.QWidget):
    """Make a widget to set the pixel size configuration"""

    def __init__(self, mmcore: Optional[CMMCorePlus] = None):
        super().__init__()

        self._mmc = mmcore or get_core_singleton()

        self.table = PixelSizeTable(self._mmc)

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

    def _delete_selected_row(self, row: Optional[int]):
        if row:
            selected_row = [row]
        else:
            selected_row = [r.row() for r in self.table.selectedIndexes()]

        if not selected_row or len(selected_row) > 1:
            return

        self.table._disconnect(selected_row[0])
        self.table.removeRow(selected_row[0])
        self._update_row_numbers()

    def _update_row_numbers(self):
        for r in range(self.table.rowCount()):
            obj_wdg = self.table.cellWidget(r, 1)
            obj_wdg.setProperty("row", r)
            mag_wdg = self.table.cellWidget(r, 1)
            mag_wdg.setProperty("row", r)
            cam_px_wdg = self.table.cellWidget(r, 2)
            cam_px_wdg.setProperty("row", r)
            img_px_wdg = self.table.cellWidget(r, 3)
            img_px_wdg.setProperty("row", r)


if __name__ == "__main__":
    import sys

    app = QtW.QApplication(sys.argv)
    win = PixelSizeWidget()
    win.show()
    sys.exit(app.exec_())
