from __future__ import annotations

from pymmcore_widgets import (
    CameraRoiWidget,
    ConfigurationWidget,
    GroupPresetTableWidget,
    ObjectivesWidget,
)
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt

from ._mda_widget import MDAWidget
from ._sample_explorer_widget._sample_explorer_widget import MMExploreSample
from ._shutters_widget import MMShuttersWidget
from ._tab_widget import MMTabWidget


class MicroManagerWidget(QtW.QWidget):
    """GUI elements for the Main Window."""

    def __init__(self):
        super().__init__()
        # sub_widgets
        self.cfg_wdg = ConfigurationWidget()
        self.obj_wdg = ObjectivesWidget()
        self.cam_wdg = CameraRoiWidget()
        self.tab_wdg = MMTabWidget()
        self.shutter_wdg = MMShuttersWidget()
        self.mda = MDAWidget()
        self.explorer = MMExploreSample()
        self.create_gui()

    def create_gui(self):
        # main widget
        self.main_layout = QtW.QVBoxLayout()
        self.main_layout.setContentsMargins(10, 0, 10, 0)
        self.main_layout.setSpacing(3)
        self.main_layout.setAlignment(Qt.AlignCenter)

        # add cfg_wdg
        self.main_layout.addWidget(self.cfg_wdg)

        # add shutters
        s_wdg = QtW.QGroupBox()
        s_l = QtW.QHBoxLayout()
        s_l.setAlignment(Qt.AlignLeft)
        s_l.setContentsMargins(5, 5, 5, 5)
        s_wdg.setLayout(s_l)
        s_l.addWidget(self.shutter_wdg)
        self.main_layout.addWidget(s_wdg)

        gp_wdg = QtW.QWidget()
        gp_l = QtW.QVBoxLayout()
        gp_l.setContentsMargins(20, 20, 20, 20)
        gp_wdg.setLayout(gp_l)
        self.group_preset_table_wdg = GroupPresetTableWidget()
        gp_l.addWidget(self.group_preset_table_wdg)

        # add tab widget
        self.main_layout.addWidget(self.tab_wdg)
        self.tab_wdg.tabWidget.addTab(self.mda, "Multi-D Acquisition")
        self.tab_wdg.tabWidget.addTab(self.explorer, "Sample Explorer")
        self.tab_wdg.tabWidget.addTab(gp_wdg, "Groups and Presets")

        # set main_layout layout
        self.setLayout(self.main_layout)
