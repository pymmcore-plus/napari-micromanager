from __future__ import annotations

from pymmcore_widgets import ConfigurationWidget, GroupPresetTableWidget
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt

from ._hcs_widget import HCSWidgetMain
from ._mda_widget import MultiDWidget
from ._sample_explorer_widget import SampleExplorer
from ._shutters_widget import MMShuttersWidget
from ._tab_widget import MMTabWidget

TOOLBAR_STYLE = """
    QToolButton { font-size: 12px; }
    QToolButton::menu-button { border: 0px; width: 20px; }
    """


class MicroManagerWidget(QtW.QWidget):
    """GUI elements for the Main Window."""

    def __init__(self):
        super().__init__()

        # sub_widgets
        self.cfg_wdg = ConfigurationWidget()
        self.cfg_wdg.setTitle("")
        self.tab_wdg = MMTabWidget()
        self.shutter_wdg = MMShuttersWidget()
        self.explorer = SampleExplorer()
        self.mda = MultiDWidget()
        self.hcs = HCSWidgetMain()

        self.setLayout(QtW.QVBoxLayout())
        self._add_menu()
        self._create_gui()

    def _add_menu(self) -> None:
        self.toolbar = QtW.QToolBar()
        self.toolbar.setMinimumHeight(30)
        self.layout().setMenuBar(self.toolbar)
        self.mm_menu = QtW.QToolButton(parent=self)
        self.mm_menu.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.mm_menu.setText("Menu")
        self.mm_menu.setMinimumWidth(75)
        self.mm_menu.setPopupMode(QtW.QToolButton.MenuButtonPopup)
        self.mm_menu.setEnabled(True)
        self.submenu = QtW.QMenu(parent=self)
        self.mm_menu.setMenu(self.submenu)
        self.mm_menu.setStyleSheet(TOOLBAR_STYLE)
        self.toolbar.addWidget(self.mm_menu)

    def _create_gui(self):
        # main widget

        self._scroll = QtW.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.main_wdg = QtW.QWidget()
        self.main_layout = QtW.QVBoxLayout()
        self.main_layout.setContentsMargins(10, 0, 10, 0)
        self.main_layout.setSpacing(3)
        self.main_layout.setAlignment(Qt.AlignCenter)
        self.main_wdg.setLayout(self.main_layout)

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
        spacer = QtW.QSpacerItem(
            10, 10, QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Expanding
        )
        gp_l.addItem(spacer)

        # add tab widget
        self.main_layout.addWidget(self.tab_wdg)
        self.tab_wdg.tabWidget.addTab(gp_wdg, "Groups and Presets")
        self.tab_wdg.tabWidget.addTab(self.mda, "Multi-D Acquisition")
        self.tab_wdg.tabWidget.addTab(self.explorer, "Sample Explorer")
        self.tab_wdg.tabWidget.addTab(self.hcs, "HCS")

        # set main_layout layout
        self._scroll.setWidget(self.main_wdg)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self._scroll)


if __name__ == "__main__":
    app = QtW.QApplication([])
    frame = MicroManagerWidget()
    frame.show()
    app.exec_()
