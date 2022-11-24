from __future__ import annotations

from pathlib import Path
from typing import cast

from fonticon_mdi6 import MDI6
from pymmcore_widgets import (
    ChannelWidget,
    ConfigurationWidget,
    DefaultCameraExposureWidget,
    LiveButton,
    ObjectivesWidget,
    SnapButton,
)
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QToolBar,
)
from superqt.fonticon import icon

from ._shutters_widget import MMShuttersWidget

PX_ICON = str(Path(__file__).parent / "icons/px_icon.png")
TOOLBAR_SIZE = 45
TOOL_SIZE = 35
GROUPBOX_STYLE = "QGroupBox { border-radius: 3px; }"
TOOLBAR_STYLE = "QToolButton::menu-indicator{ image: none; }"
PUSHBUTTON_STYLE = """
        color: rgb(0, 255, 0);
        font-weight: bold;
    """


class MicroManagerWidget(QMainWindow):
    """GUI elements for the Main Window."""

    def __init__(self) -> None:
        super().__init__()

        # widgets
        self.cfg_wdg = ConfigurationWidget()
        self.shutter_wdg = MMShuttersWidget()
        self.exposure_widget = DefaultCameraExposureWidget()
        self.obj_wdg = ObjectivesWidget()
        self.snap_button = SnapButton()
        self.live_button = LiveButton()

        self._createToolBars()

    def _createToolBars(self) -> None:

        cfg = self._add_cfg()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, cfg)

        # objectives
        obj = self._add_objective()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, obj)

        # # break
        # self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)

        # channel exposure
        ch = self._add_channels()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, ch)

        # exposure
        exp = self._add_exposure()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, exp)

        # snap live
        snap_live_toolbar = self._add_snap_live_toolbar()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, snap_live_toolbar)

        # tools (cam roi, illumination, stages, ...)
        tools = self._add_tools_buttons()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tools)

        # plugins (mda, explorer, ...)
        plugins = self._add_plugins_toolbar()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, plugins)

        # shutter
        self.shutters_toolbar = self._add_shutter_toolbar()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.shutters_toolbar)

    def _create_groupbox(self) -> QGroupBox:
        wdg = QGroupBox()
        wdg.setLayout(QHBoxLayout())
        wdg.layout().setContentsMargins(5, 0, 5, 0)
        wdg.layout().setSpacing(0)
        return wdg

    def _add_cfg(self) -> QToolBar:
        cfg_toolbar = QToolBar("Configuration", self)
        cfg_toolbar.setMinimumHeight(TOOLBAR_SIZE)
        cfg_toolbar.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.cfg_wdg.setStyleSheet(GROUPBOX_STYLE)
        self.cfg_wdg.setTitle("")
        self.cfg_wdg.layout().setContentsMargins(5, 0, 5, 0)
        cfg_toolbar.addWidget(self.cfg_wdg)

        return cfg_toolbar

    def _add_objective(self) -> QToolBar:
        obj_toolbar = QToolBar("Objectives", self)
        obj_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.setStyleSheet(GROUPBOX_STYLE)
        # TODO: add this directrly to ObjectivesWidget
        self.obj_wdg.setMinimumWidth(0)
        self.obj_wdg._mmc.events.systemConfigurationLoaded.connect(self._resize_obj)
        self.obj_wdg._combo.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        wdg.layout().addWidget(self.obj_wdg)
        obj_toolbar.addWidget(wdg)

        return obj_toolbar

    # TODO: add this directrly to ObjectivesWidget
    def _resize_obj(self) -> None:
        self.obj_wdg._combo.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.obj_wdg.setMinimumWidth(0)
        self.obj_wdg._combo.adjustSize()

    def _add_snap_live_toolbar(self) -> QToolBar:
        snap_live_toolbar = QToolBar("Snap Live", self)
        snap_live_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.layout().setSpacing(3)
        wdg.setStyleSheet("border: 0px;")

        self.snap_button.setText("")
        self.snap_button.setToolTip("Snap")
        self.snap_button.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        wdg.layout().addWidget(self.snap_button)

        self.live_button.setText("")
        self.live_button.setToolTip("Live Mode")
        self.live_button.button_text_off = ""
        self.live_button.button_text_on = ""
        self.live_button.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        wdg.layout().addWidget(self.live_button)

        snap_live_toolbar.addWidget(wdg)

        return snap_live_toolbar

    def _add_channels(self) -> QToolBar:
        ch_toolbar = QToolBar("Channels", self)
        ch_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.setStyleSheet(GROUPBOX_STYLE)

        ch_lbl = QLabel(text="Channel:")
        wdg.layout().addWidget(ch_lbl)
        self.channel_combo = ChannelWidget()
        wdg.layout().addWidget(self.channel_combo)

        ch_toolbar.addWidget(wdg)

        return ch_toolbar

    def _add_exposure(self) -> QToolBar:
        exp_toolbar = QToolBar("Exposure", self)
        exp_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.setStyleSheet(GROUPBOX_STYLE)

        exp_lbl = QLabel(text="Exposure:")
        exp_layout = cast(QHBoxLayout, self.exposure_widget.layout())
        exp_layout.setContentsMargins(0, 0, 0, 0)
        exp_layout.setSpacing(3)
        exp_layout.insertWidget(0, exp_lbl)
        wdg.layout().addWidget(self.exposure_widget)

        exp_toolbar.addWidget(wdg)

        return exp_toolbar

    def _add_shutter_toolbar(self) -> QToolBar:
        shutters_toolbar = QToolBar("Shutters", self)
        shutters_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.layout().setSpacing(3)
        wdg.setStyleSheet("border: 0px;")

        self.shutter_wdg.setMinimumHeight(TOOL_SIZE)
        wdg.layout().addWidget(self.shutter_wdg)

        shutters_toolbar.addWidget(wdg)

        return shutters_toolbar

    def _add_tools_buttons(self) -> QToolBar:
        tools_toolbar = QToolBar("Tools", self)
        tools_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.layout().setSpacing(3)
        wdg.setStyleSheet("border: 0px;")

        self.prop_browser_btn = QPushButton(parent=self)
        self.prop_browser_btn.setToolTip("Property Browser")
        self.prop_browser_btn.setEnabled(False)
        self.prop_browser_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.prop_browser_btn.setIcon(icon(MDI6.table_large, color=(0, 255, 0)))
        self.prop_browser_btn.setIconSize(QSize(30, 30))
        wdg.layout().addWidget(self.prop_browser_btn)

        self.gp_button = QPushButton()
        self.gp_button.setToolTip("Group & Preset Table")
        self.gp_button.setEnabled(False)
        self.gp_button.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.gp_button.setIcon(icon(MDI6.table_large_plus, color=(0, 255, 0)))
        self.gp_button.setIconSize(QSize(30, 30))
        wdg.layout().addWidget(self.gp_button)

        self.stage_btn = QPushButton(parent=self)
        self.stage_btn.setToolTip("Stages Control")
        self.stage_btn.setEnabled(False)
        self.stage_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.stage_btn.setIcon(icon(MDI6.arrow_all, color=(0, 255, 0)))
        self.stage_btn.setIconSize(QSize(30, 30))
        wdg.layout().addWidget(self.stage_btn)

        self.ill_btn = QPushButton(parent=self)
        self.ill_btn.setToolTip("Illumination Control")
        self.ill_btn.setEnabled(False)
        self.ill_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.ill_btn.setIcon(icon(MDI6.lightbulb_on, color=(0, 255, 0)))
        self.ill_btn.setIconSize(QSize(30, 30))
        wdg.layout().addWidget(self.ill_btn)

        self.px_btn = QPushButton(parent=self)
        self.px_btn.setToolTip("Set Pixel Size")
        self.px_btn.setEnabled(False)
        self.px_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.px_btn.setIcon(QIcon(PX_ICON))
        self.px_btn.setIconSize(QSize(30, 30))
        wdg.layout().addWidget(self.px_btn)

        self.cam_btn = QPushButton(parent=self)
        self.cam_btn.setToolTip("Camera ROI")
        self.cam_btn.setEnabled(False)
        self.cam_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.cam_btn.setIcon(icon(MDI6.crop, color=(0, 255, 0)))
        self.cam_btn.setIconSize(QSize(30, 30))
        wdg.layout().addWidget(self.cam_btn)

        tools_toolbar.addWidget(wdg)

        return tools_toolbar

    def _add_plugins_toolbar(self) -> QToolBar:
        plgs_toolbar = QToolBar("Plugins")
        plgs_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = QGroupBox()
        wdg.setLayout(QHBoxLayout())
        wdg.layout().setContentsMargins(5, 0, 5, 0)
        wdg.layout().setSpacing(3)
        wdg.setStyleSheet("border: 0px;")

        self.mda_button = QPushButton(text="MDA")
        self.mda_button.setToolTip("MultiDimensional Acquisition")
        self.mda_button.setMinimumHeight(TOOL_SIZE)
        wdg.layout().addWidget(self.mda_button)

        self.explorer_button = QPushButton(text="Explorer")
        self.explorer_button.setToolTip("MultiDimensional Grid Acqiosition")
        self.explorer_button.setMinimumHeight(TOOL_SIZE)
        wdg.layout().addWidget(self.explorer_button)

        plgs_toolbar.addWidget(wdg)

        return plgs_toolbar
