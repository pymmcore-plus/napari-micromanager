from __future__ import annotations

from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt
from superqt import QCollapsible

from ._gui_objects._camera_widget import MMCameraWidget
from ._gui_objects._illumination_widget import MMIlluminationWidget
from ._gui_objects._mm_configuration_widget import MMConfigurationWidget
from ._gui_objects._objective_widget import MMObjectivesWidget
from ._gui_objects._property_browser_widget import MMPropertyBrowserWidget
from ._gui_objects._tab_widget import MMTabWidget
from ._gui_objects._xyz_stages import MMStagesWidget


class MicroManagerWidget(QtW.QWidget):
    def __init__(self):
        super().__init__()

        # sub_widgets
        self.mm_configuration = MMConfigurationWidget()
        self.mm_objectives = MMObjectivesWidget()
        self.mm_illumination = MMIlluminationWidget()
        self.mm_prop_browser = MMPropertyBrowserWidget()
        self.mm_camera = MMCameraWidget()
        self.mm_xyz_stages = MMStagesWidget()
        self.mm_tab = MMTabWidget()

    def create_gui(self):

        # main widget
        # self.setMinimumWidth(600)
        self.main_layout = QtW.QGridLayout()
        self.main_layout.setContentsMargins(10, 0, 10, 0)
        self.main_layout.setVerticalSpacing(3)
        self.main_layout.setHorizontalSpacing(0)
        self.main_layout.setAlignment(Qt.AlignCenter)

        # add all widgets to main_layout
        self.main_layout.addWidget(self.mm_configuration, 0, 0)

        # add camera collapsible
        self.cam_group = QtW.QGroupBox()
        self.cam_group_layout = QtW.QGridLayout()
        self.cam_group_layout.setSpacing(0)
        self.cam_group_layout.setContentsMargins(0, 0, 0, 0)
        self.camera_coll = QCollapsible(title="Camera")
        self.camera_coll.layout().setSpacing(0)
        self.camera_coll.addWidget(self.mm_camera)
        self.camera_coll.expand(animate=False)
        self.cam_group_layout.addWidget(self.camera_coll)
        self.cam_group.setLayout(self.cam_group_layout)
        self.main_layout.addWidget(self.cam_group, 2, 0)

        # add stages collapsible
        self.stages_group = QtW.QGroupBox()
        self.stages_group_layout = QtW.QGridLayout()
        self.stages_group_layout.setSpacing(0)
        self.stages_group_layout.setContentsMargins(0, 0, 0, 0)
        self.stages_coll = QCollapsible(title="Stages")
        self.stages_coll.layout().setSpacing(0)
        self.stages_coll.addWidget(self.mm_xyz_stages)
        self.stages_coll.expand(animate=False)
        self.stages_group_layout.addWidget(self.stages_coll)
        self.stages_group.setLayout(self.stages_group_layout)
        self.main_layout.addWidget(self.stages_group, 3, 0)

        self.main_layout.addWidget(self.mm_tab, 4, 0)

        obj_ill = self.add_mm_objectives_and_illumination_widgets()
        self.main_layout.addWidget(obj_ill, 1, 0)

        # set main_layout layout
        self.setLayout(self.main_layout)

    def add_mm_objectives_and_illumination_widgets(self):

        # main objectives, illumination and camera widget
        wdg = QtW.QWidget()
        wdg_layout = QtW.QGridLayout()
        wdg_layout.setContentsMargins(0, 0, 0, 0)
        wdg_layout.setHorizontalSpacing(0)
        wdg_layout.setVerticalSpacing(0)

        wdg_layout.addWidget(self.mm_objectives, 0, 0)
        wdg_layout.addWidget(self.mm_illumination, 0, 1)
        wdg_layout.addWidget(self.mm_prop_browser, 0, 2)

        wdg.setLayout(wdg_layout)

        return wdg
