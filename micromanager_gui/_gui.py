from __future__ import annotations

from qtpy import QtWidgets as QtW

from ._gui_objects._camera_widget import MMCameraWidget
from ._gui_objects._illumination_widget import MMIlluminationWidget
from ._gui_objects._mm_configuration_widget import MMConfigurationWidget
from ._gui_objects._objective_widget import MMObjectivesWidget
from ._gui_objects._tab_widget import MMTabWidget
from ._gui_objects._xyz_stages import MMStagesWidget


class MicroManagerWidget(QtW.QWidget):
    def __init__(self):
        super().__init__()

        # sub_widgets
        self.mm_configuration = MMConfigurationWidget()
        self.mm_objectives = MMObjectivesWidget()
        self.mm_illumination = MMIlluminationWidget()
        self.mm_camera = MMCameraWidget()
        self.mm_xyz_stages = MMStagesWidget()
        self.mm_tab = MMTabWidget()

        self.create_gui()

    def create_gui(self):

        # main widget
        self.main_layout = QtW.QGridLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # add all widgets to main_layout
        self.main_layout.addWidget(self.mm_configuration, 0, 0)
        self.main_layout.addWidget(self.mm_xyz_stages, 2, 0)
        self.main_layout.addWidget(self.mm_tab, 3, 0)
        self.add_mm_objectives_illumination_camera_widget()

        # set main_layout layout
        self.setLayout(self.main_layout)

    def add_mm_objectives_illumination_camera_widget(self):

        # main objectives, illumination and camera widget
        wdg_1 = QtW.QWidget()
        wdg_1_layout = QtW.QGridLayout()
        wdg_1_layout.setContentsMargins(0, 0, 0, 0)
        wdg_1_layout.setSpacing(0)

        # create objectives and illumination widget
        wdg_2 = QtW.QWidget()
        wdg_2.setMaximumHeight(135)
        wdg_2_layout = QtW.QGridLayout()
        wdg_2_layout.setContentsMargins(0, 0, 0, 0)
        wdg_2_layout.setSpacing(0)
        wdg_2_layout.addWidget(self.mm_objectives, 0, 0)
        wdg_2_layout.addWidget(self.mm_illumination, 1, 0)
        # set layout wdg_2
        wdg_2.setLayout(wdg_2_layout)

        # add objectives and illumination widgets to wdg 1
        wdg_1_layout.addWidget(wdg_2, 0, 0)

        # add camera widget to wdg 1
        wdg_1_layout.addWidget(self.mm_camera, 0, 1)

        # set layout wdg_1
        wdg_1.setLayout(wdg_1_layout)

        # add wdg_1 to main_layout
        self.main_layout.addWidget(wdg_1, 1, 0)
