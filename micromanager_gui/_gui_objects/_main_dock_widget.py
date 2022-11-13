from typing import Optional

from pymmcore_widgets import CameraRoiWidget
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QDockWidget, QHBoxLayout, QMainWindow, QSizePolicy, QWidget

from ._group_preset_wdg import GroupPreset
from ._illumination_widget import IlluminationWidget
from ._stages_widget import MMStagesWidget


class _MainDockWidget(QMainWindow):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.group_preset_table_wdg = GroupPreset()
        dock_gp = QDockWidget("Groups&Presets", self)
        wdg_gp = QWidget()
        wdg_gp.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        wdg_gp.setLayout(QHBoxLayout())
        wdg_gp.layout().setContentsMargins(0, 0, 0, 0)
        wdg_gp.layout().addWidget(self.group_preset_table_wdg)
        dock_gp.setWidget(wdg_gp)
        self.addDockWidget(Qt.TopDockWidgetArea, dock_gp)

        self.illumination = IlluminationWidget()
        dock_ill = QDockWidget("Illumination", self)
        wdg_ill = QWidget()
        wdg_ill.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        wdg_ill.setLayout(QHBoxLayout())
        wdg_ill.layout().setContentsMargins(0, 0, 0, 0)
        wdg_ill.layout().addWidget(self.illumination)
        dock_ill.setWidget(wdg_ill)
        self.addDockWidget(Qt.TopDockWidgetArea, dock_ill)
        # dock_ill.hide()

        self.splitDockWidget(dock_gp, dock_ill, Qt.Vertical)

        self.stages = MMStagesWidget()
        dock_stg = QDockWidget("Stages", self)
        wdg_stg = QWidget()
        wdg_stg.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        wdg_stg.setLayout(QHBoxLayout())
        wdg_stg.layout().setContentsMargins(0, 0, 0, 0)
        wdg_stg.layout().addWidget(self.stages)
        dock_stg.setWidget(wdg_stg)
        self.addDockWidget(Qt.TopDockWidgetArea, dock_stg)
        # dock_stg.hide()

        self.splitDockWidget(dock_ill, dock_stg, Qt.Vertical)

        self.cam_roi = CameraRoiWidget()
        dock_cam = QDockWidget("Camera ROI", self)
        wdg_cam = QWidget()
        wdg_cam.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        wdg_cam.setLayout(QHBoxLayout())
        wdg_cam.layout().setContentsMargins(0, 0, 0, 0)
        wdg_cam.layout().addWidget(self.cam_roi)
        dock_cam.setWidget(wdg_cam)
        self.addDockWidget(Qt.TopDockWidgetArea, dock_cam)
        # dock_cam.hide()

        self.splitDockWidget(dock_stg, dock_cam, Qt.Vertical)
