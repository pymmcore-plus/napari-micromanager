from __future__ import annotations

from pymmcore_widgets import ConfigurationWidget, GroupPresetTableWidget
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt
from superqt import QCollapsible

from ._mda_widget._mda_widget import MMMultiDWidget
from ._sample_explorer_widget._sample_explorer_widget import MMExploreSample
from ._shutters_widget import MMShuttersWidget
from ._tab_widget import MMTabWidget
from ._xyz_stages import MMStagesWidget

TOOLBAR_STYLE = """
    QToolButton { font-size: 13px; }
    QToolButton::menu-button { border: 0px; width: 20px; height: 20px; }
    """


class MicroManagerWidget(QtW.QWidget):
    """GUI elements for the Main Window."""

    def __init__(self):
        super().__init__()
        # sub_widgets
        self.cfg_wdg = ConfigurationWidget()
        self.cfg_wdg.setTitle("")
        self.stage_wdg = MMStagesWidget()
        self.tab_wdg = MMTabWidget()
        self.shutter_wdg = MMShuttersWidget()
        self.mda = MMMultiDWidget()
        self.explorer = MMExploreSample()
        self.group_preset_table_wdg = GroupPresetTableWidget()

        self.setLayout(QtW.QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.create_gui()
        self._add_menu()

    def _add_menu(self) -> None:
        self.toolbar = QtW.QToolBar()
        self.toolbar.setMinimumHeight(40)
        self.layout().setMenuBar(self.toolbar)

        self.mm_menu = QtW.QToolButton(parent=self)
        self.mm_menu.setText("Menu")
        self.mm_menu.setMinimumWidth(75)
        self.mm_menu.setPopupMode(QtW.QToolButton.MenuButtonPopup)
        self.submenu = QtW.QMenu(parent=self)
        self.mm_menu.setMenu(self.submenu)
        self.mm_menu.setStyleSheet(TOOLBAR_STYLE)
        self.toolbar.addWidget(self.mm_menu)

    def create_gui(self):
        # main scroll area
        self._scroll = QtW.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self._scroll)
        # main widget
        self.main_wdg = QtW.QWidget()
        self.main_layout = QtW.QVBoxLayout()
        self.main_layout.setContentsMargins(10, 0, 10, 0)
        self.main_layout.setSpacing(3)
        self.main_layout.setAlignment(Qt.AlignCenter)
        self.main_wdg.setLayout(self.main_layout)
        # add cfg_wdg
        self.main_layout.addWidget(self.cfg_wdg)
        # add shutters
        sh = self.add_shutter_widgets()
        self.main_layout.addWidget(sh)
        # add stages collapsible
        stages_group = self._add_stage_collapsible()
        self.main_layout.addWidget(stages_group)
        # add tab widget
        gp = self._add_group_preset_wdg()
        self.main_layout.addWidget(self.tab_wdg)
        self.tab_wdg.tabWidget.addTab(gp, "Groups and Presets")
        self.tab_wdg.tabWidget.addTab(self.mda, "Multi-D Acquisition")
        self.tab_wdg.tabWidget.addTab(self.explorer, "Sample Explorer")
        # add to scroll
        self._scroll.setWidget(self.main_wdg)

    def _add_group_preset_wdg(self):
        wdg = QtW.QWidget()
        layout = QtW.QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        wdg.setLayout(layout)
        layout.addWidget(self.group_preset_table_wdg)
        return wdg

    def add_shutter_widgets(self):
        shutter_wdg = QtW.QGroupBox()
        shutter_wdg_layout = QtW.QHBoxLayout()
        shutter_wdg_layout.setAlignment(Qt.AlignLeft)
        shutter_wdg_layout.setContentsMargins(5, 5, 5, 5)
        shutter_wdg_layout.setSpacing(7)
        shutter_wdg_layout.addWidget(self.shutter_wdg)
        shutter_wdg.setLayout(shutter_wdg_layout)
        return shutter_wdg

    def _add_stage_collapsible(self):
        stages_group = QtW.QGroupBox()
        stages_group_layout = QtW.QVBoxLayout()
        stages_group_layout.setSpacing(0)
        stages_group_layout.setContentsMargins(1, 0, 1, 1)
        stages_group.setLayout(stages_group_layout)

        self.stages_coll = QCollapsible(title="Stages")
        self.stages_coll.setSizePolicy(
            QtW.QSizePolicy(QtW.QSizePolicy.Minimum, QtW.QSizePolicy.Fixed)
        )
        self.stages_coll.layout().setSpacing(0)
        self.stages_coll.layout().setContentsMargins(0, 0, 0, 0)
        self.stages_coll.addWidget(self.stage_wdg)
        stages_group_layout.addWidget(self.stages_coll)
        return stages_group
