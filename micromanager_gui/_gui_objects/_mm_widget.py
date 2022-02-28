from __future__ import annotations

from qtpy import QtWidgets as QtW

from ._camera_widget import MMCameraWidget
from ._illumination_widget import MMIlluminationWidget
from ._mm_configuration_widget import MMConfigurationWidget
from ._objective_widget import MMObjectivesWidget
from ._tab_widget import MMTabWidget
from ._xyz_stages import MMStagesWidget


class MicroManagerWidget(QtW.QWidget):
    def __init__(self):
        super().__init__()

        # sub_widgets
        self.cfg_wdg = MMConfigurationWidget()
        self.obj_wdg = MMObjectivesWidget()
        self.illum_wdg = MMIlluminationWidget()
        self.cam_wdg = MMCameraWidget()
        self.stage_wdg = MMStagesWidget()
        self.tab_wdg = MMTabWidget()

        # create objectives and illumination widget
        obj_illum = QtW.QWidget()
        obj_illum.setLayout(QtW.QVBoxLayout())
        obj_illum.layout().setContentsMargins(0, 0, 0, 0)
        obj_illum.layout().setSpacing(0)
        obj_illum.layout().addWidget(self.obj_wdg)
        obj_illum.layout().addWidget(self.illum_wdg)

        # main objectives, illumination and camera widget
        obj_cam_illum = QtW.QWidget()
        obj_cam_illum.setLayout(QtW.QHBoxLayout())
        obj_cam_illum.layout().setContentsMargins(0, 0, 0, 0)
        obj_cam_illum.layout().addWidget(obj_illum)
        obj_cam_illum.layout().addWidget(self.cam_wdg)

        # main widget
        self.setLayout(QtW.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.layout().addWidget(self.cfg_wdg)
        self.layout().addWidget(obj_cam_illum)
        self.layout().addWidget(self.stage_wdg)
        self.layout().addWidget(self.tab_wdg)
