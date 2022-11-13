from __future__ import annotations

from fonticon_mdi6 import MDI6
from pymmcore_widgets import (
    ChannelWidget,
    ConfigurationWidget,
    DefaultCameraExposureWidget,
    LiveButton,
    ObjectivesWidget,
    SnapButton,
)
from qtpy import QtWidgets as QtW
from qtpy.QtCore import QSize, Qt
from superqt.fonticon import icon

from ._shutters_widget import MMShuttersWidget

TOOLBAR_SIZE = 45
TOOL_SIZE = 35
GROUPBOX_STYLE = "QGroupBox { border-radius: 3px; }"
TOOLBAR_STYLE = "QToolButton::menu-indicator{ image: none; }"
MENU_STYLE = """
    QMenu {
        font-size: 15px;
        border: 1px solid grey;
        border-radius: 3px;
    }
"""
PUSHBUTTON_STYLE = """
        color: rgb(0, 255, 0);
        font-weight: bold;
    """


class MicroManagerWidget(QtW.QMainWindow):
    """GUI elements for the Main Window."""

    def __init__(self):
        super().__init__()

        # widgets
        self.cfg_wdg = ConfigurationWidget()
        self.shutter_wdg = MMShuttersWidget()
        self.exposure_widget = DefaultCameraExposureWidget()
        self.obj_wdg = ObjectivesWidget()
        self.snap_button = SnapButton()
        self.live_button = LiveButton()

        self._createToolBars()

        base_wdg = QtW.QWidget()
        base_wdg.setLayout(QtW.QVBoxLayout())
        base_wdg.setSizePolicy(QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Expanding)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(base_wdg)
        self.setCentralWidget(base_wdg)

    def _createToolBars(self):
        # self.menu_toolbar = QtW.QToolBar("Menu", self)
        # self.menu_toolbar.setMaximumHeight(TOOLBAR_SIZE)
        # self.addToolBar(Qt.TopToolBarArea, self.menu_toolbar)

        # toolbar_btn = self._add_menu_button()
        # self.menu_toolbar.addWidget(toolbar_btn)

        cfg = self._add_cfg()
        self.addToolBar(Qt.TopToolBarArea, cfg)

        # objectives
        obj = self._add_objective()
        self.addToolBar(Qt.TopToolBarArea, obj)

        # break
        self.addToolBarBreak(Qt.TopToolBarArea)

        # channel exposure
        ch = self._add_channels()
        self.addToolBar(Qt.TopToolBarArea, ch)

        # exposure
        exp = self._add_exposure()
        self.addToolBar(Qt.TopToolBarArea, exp)

        # snap live
        snap_live_toolbar = self._add_snap_live_toolbar()
        self.addToolBar(Qt.TopToolBarArea, snap_live_toolbar)

        # tools (cam roi, illumination, stages, ...)
        tools = self._add_tools_buttons()
        self.addToolBar(Qt.TopToolBarArea, tools)

        # shutter
        self.shutters_toolbar = self._add_shutter_toolbar()
        self.addToolBar(Qt.TopToolBarArea, self.shutters_toolbar)

    def _create_groupbox(self) -> QtW.QGroupBox:
        wdg = QtW.QGroupBox()
        wdg.setLayout(QtW.QHBoxLayout())
        wdg.layout().setContentsMargins(5, 0, 5, 0)
        wdg.layout().setSpacing(0)
        return wdg

    def _add_menu_button(self) -> QtW.QGroupBox:

        wdg = self._create_groupbox()
        wdg.setStyleSheet("border: 0px;")

        toolbar_menu_btn = QtW.QToolButton(parent=self)
        toolbar_menu_btn.setPopupMode(QtW.QToolButton.InstantPopup)
        toolbar_menu_btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
        toolbar_menu_btn.setLayoutDirection(Qt.RightToLeft)
        toolbar_menu_btn.setIcon(icon(MDI6.chevron_down, color=(0, 255, 0)))
        toolbar_menu_btn.setIconSize(QSize(30, 30))
        toolbar_menu_btn.setStyleSheet(TOOLBAR_STYLE)

        wdg.layout().addWidget(toolbar_menu_btn)

        self.menu = QtW.QMenu(parent=self)
        self.menu.setStyleSheet(MENU_STYLE)
        toolbar_menu_btn.setMenu(self.menu)

        return wdg

    def _add_cfg(self) -> QtW.QToolBar:
        cfg_toolbar = QtW.QToolBar("Configuration", self)
        cfg_toolbar.setMinimumHeight(TOOLBAR_SIZE)
        cfg_toolbar.setSizePolicy(QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Fixed)

        self.cfg_wdg.setStyleSheet(GROUPBOX_STYLE)
        self.cfg_wdg.setTitle("")
        self.cfg_wdg.layout().setContentsMargins(5, 0, 5, 0)
        cfg_toolbar.addWidget(self.cfg_wdg)

        return cfg_toolbar

    def _add_objective(self) -> QtW.QToolBar:
        obj_toolbar = QtW.QToolBar("Objectives", self)
        obj_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.setStyleSheet(GROUPBOX_STYLE)
        # TODO: add this directrly to ObjectivesWidget
        self.obj_wdg.setMinimumWidth(0)
        self.obj_wdg._mmc.events.systemConfigurationLoaded.connect(self._resize_obj)
        self.obj_wdg._combo.setSizePolicy(QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Fixed)
        wdg.layout().addWidget(self.obj_wdg)
        obj_toolbar.addWidget(wdg)

        return obj_toolbar

    # TODO: add this directrly to ObjectivesWidget
    def _resize_obj(self):
        self.obj_wdg._combo.setSizePolicy(QtW.QSizePolicy.Fixed, QtW.QSizePolicy.Fixed)
        self.obj_wdg.setMinimumWidth(0)
        self.obj_wdg._combo.adjustSize()

    def _add_snap_live_toolbar(self) -> QtW.QToolBar:
        snap_live_toolbar = QtW.QToolBar("Snap Live", self)
        snap_live_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.layout().setSpacing(3)
        wdg.setStyleSheet("border: 0px;")

        self.snap_button.setText("")
        self.snap_button.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        wdg.layout().addWidget(self.snap_button)

        self.live_button.setText("")
        self.live_button.button_text_off = ""
        self.live_button.button_text_on = ""
        self.live_button.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        wdg.layout().addWidget(self.live_button)

        snap_live_toolbar.addWidget(wdg)

        return snap_live_toolbar

    def _add_channels(self) -> QtW.QToolBar:
        ch_toolbar = QtW.QToolBar("Channels", self)
        ch_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.setStyleSheet(GROUPBOX_STYLE)

        ch_lbl = QtW.QLabel(text="Channel:")
        wdg.layout().addWidget(ch_lbl)
        self.channel_combo = ChannelWidget()
        wdg.layout().addWidget(self.channel_combo)

        ch_toolbar.addWidget(wdg)

        return ch_toolbar

    def _add_exposure(self) -> QtW.QToolBar:
        exp_toolbar = QtW.QToolBar("Exposure", self)
        exp_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.setStyleSheet(GROUPBOX_STYLE)

        exp_lbl = QtW.QLabel(text="Exposure:")
        self.exposure_widget.layout().setContentsMargins(0, 0, 0, 0)
        self.exposure_widget.layout().setSpacing(3)
        self.exposure_widget.layout().insertWidget(0, exp_lbl)
        wdg.layout().addWidget(self.exposure_widget)

        exp_toolbar.addWidget(wdg)

        return exp_toolbar

    def _add_shutter_toolbar(self) -> QtW.QToolBar:
        shutters_toolbar = QtW.QToolBar("Shutters", self)
        shutters_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.layout().setSpacing(3)
        wdg.setStyleSheet("border: 0px;")

        self.shutter_wdg.setMinimumHeight(TOOL_SIZE)
        wdg.layout().addWidget(self.shutter_wdg)

        shutters_toolbar.addWidget(wdg)

        return shutters_toolbar

    def _add_tools_buttons(self) -> QtW.QToolBar:
        tools_toolbar = QtW.QToolBar("Tools", self)
        tools_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.layout().setSpacing(3)
        wdg.setStyleSheet("border: 0px;")

        self.prop_browser_btn = QtW.QPushButton(parent=self)
        self.prop_browser_btn.setEnabled(False)
        self.prop_browser_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.prop_browser_btn.setIcon(icon(MDI6.table_large, color=(0, 255, 0)))
        self.prop_browser_btn.setIconSize(QSize(30, 30))
        wdg.layout().addWidget(self.prop_browser_btn)

        self.gp_button = QtW.QPushButton()
        self.gp_button.setEnabled(False)
        self.gp_button.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.gp_button.setIcon(icon(MDI6.table_large_plus, color=(0, 255, 0)))
        self.gp_button.setIconSize(QSize(30, 30))
        wdg.layout().addWidget(self.gp_button)

        self.stage_btn = QtW.QPushButton(parent=self)
        self.stage_btn.setEnabled(False)
        self.stage_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.stage_btn.setIcon(icon(MDI6.arrow_all, color=(0, 255, 0)))
        self.stage_btn.setIconSize(QSize(30, 30))
        wdg.layout().addWidget(self.stage_btn)

        self.ill_btn = QtW.QPushButton(parent=self)
        self.ill_btn.setEnabled(False)
        self.ill_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.ill_btn.setIcon(icon(MDI6.lightbulb_on, color=(0, 255, 0)))
        self.ill_btn.setIconSize(QSize(30, 30))
        wdg.layout().addWidget(self.ill_btn)

        self.px_btn = QtW.QPushButton(text="PX", parent=self)
        self.px_btn.setStyleSheet(PUSHBUTTON_STYLE)
        self.px_btn.setEnabled(False)
        self.px_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        wdg.layout().addWidget(self.px_btn)

        self.cam_btn = QtW.QPushButton(parent=self)
        self.cam_btn.setEnabled(False)
        self.cam_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.cam_btn.setIcon(icon(MDI6.crop, color=(0, 255, 0)))
        self.cam_btn.setIconSize(QSize(30, 30))
        wdg.layout().addWidget(self.cam_btn)

        self.log_btn = QtW.QPushButton(parent=self)
        self.log_btn.setEnabled(False)
        self.log_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.log_btn.setIcon(icon(MDI6.math_log, color=(0, 255, 0)))
        self.log_btn.setIconSize(QSize(30, 30))
        wdg.layout().addWidget(self.log_btn)

        tools_toolbar.addWidget(wdg)

        return tools_toolbar
