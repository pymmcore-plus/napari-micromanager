from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Dict, Tuple, cast

from fonticon_mdi6 import MDI6
from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import (
    CameraRoiWidget,
    ChannelWidget,
    ConfigurationWidget,
    DefaultCameraExposureWidget,
    GroupPresetTableWidget,
    LiveButton,
    ObjectivesWidget,
    PixelSizeWidget,
    PropertyBrowser,
    SnapButton,
)
from qtpy.QtCore import QEvent, QObject, QSize, Qt
from qtpy.QtWidgets import (
    QDockWidget,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QToolBar,
    QWidget,
)
from superqt.fonticon import icon

from ._illumination_widget import IlluminationWidget
from ._mda_widget import MultiDWidget
from ._min_max_widget import MinMax
from ._shutters_widget import MMShuttersWidget
from ._stages_widget import MMStagesWidget

if TYPE_CHECKING:
    import napari.viewer

TOOLBAR_SIZE = 45
TOOL_SIZE = 35
GROUPBOX_STYLE = "QGroupBox { border-radius: 3px; }"


# Dict for QObject and its QPushButton icon
DOCK_WIDGETS: Dict[str, Tuple[type[QWidget], str | None]] = {  # noqa: U006
    "Device Property Browser": (PropertyBrowser, MDI6.table_large),
    "Groups and Presets Table": (GroupPresetTableWidget, MDI6.table_large_plus),
    "Illumination Control": (IlluminationWidget, MDI6.lightbulb_on),
    "Stages Control": (MMStagesWidget, MDI6.arrow_all),
    "Camera ROI": (CameraRoiWidget, MDI6.crop),
    "Pixel Size Table": (PixelSizeWidget, MDI6.ruler),
    "MDA": (MultiDWidget, None),
}


class MicroManagerToolbar(QMainWindow):
    """Create a QToolBar for the Main Window."""

    def __init__(self, viewer: napari.viewer.Viewer) -> None:
        super().__init__()

        self._mmc = CMMCorePlus.instance()
        self.viewer: napari.viewer.Viewer = getattr(viewer, "__wrapped__", viewer)

        # min max widget
        self.minmax = MinMax(parent=self)

        if (win := getattr(self.viewer.window, "_qt_window", None)) is not None:
            # make the tabs of tabbed dockwidgets apprearing on top (North)
            areas = [
                Qt.DockWidgetArea.RightDockWidgetArea,
                Qt.DockWidgetArea.LeftDockWidgetArea,
                Qt.DockWidgetArea.TopDockWidgetArea,
                Qt.DockWidgetArea.BottomDockWidgetArea,
            ]
            for area in areas:
                cast(QMainWindow, win).setTabPosition(
                    area, QTabWidget.TabPosition.North
                )

        self._dock_widgets: dict[str, QDockWidget] = {}

        # add toolbar items
        toolbar_items = [
            self._add_cfg(),
            self._add_objective(),
            self._add_channels(),
            self._add_exposure(),
            self._add_snap_live_toolbar(),
            self._add_tools_toolsbar(),
            self._add_plugins_toolbar(),
            "",
            self._add_shutter_toolbar(),
        ]
        for item in toolbar_items:
            if not item:
                self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
                continue
            self.addToolBar(Qt.ToolBarArea.TopToolBarArea, item)

        self.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Event filter that ensures that this widget is shown at the top.

        npe2 plugins don't have a way to specify where they should be added, so this
        event filter listens for the event when this widget is docked in the main
        window, then redocks it at the top and assigns allowed areas.
        """
        # the move event is one of the first events that is fired when the widget is
        # docked, so we use it to re-dock this widget at the top
        if event.type() == QEvent.Type.Move and obj is self:
            dw = self.parent()
            if not (win := getattr(self.viewer.window, "_qt_window", None)):
                return False
            win = cast(QMainWindow, win)
            if (
                isinstance(dw, QDockWidget)
                and win.dockWidgetArea(dw) is not Qt.DockWidgetArea.TopDockWidgetArea
            ):
                was_visible = dw.isVisible()
                win.removeDockWidget(dw)
                dw.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea)
                win.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, dw)
                dw.setVisible(was_visible)  # necessary after using removeDockWidget
        return False

    def _add_cfg(self) -> QToolBar:
        """Create a QToolBar with the `ConfigurationWidget`."""
        cfg_toolbar = QToolBar("Configuration", self)
        cfg_toolbar.setMinimumHeight(TOOLBAR_SIZE)
        cfg_toolbar.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        cfg_wdg = ConfigurationWidget()
        cfg_wdg.setStyleSheet(GROUPBOX_STYLE)
        cfg_wdg.setTitle("")
        cfg_wdg.layout().setContentsMargins(5, 0, 5, 0)
        cfg_toolbar.addWidget(cfg_wdg)

        return cfg_toolbar

    def _create_groupbox(self) -> QGroupBox:
        wdg = QGroupBox()
        wdg.setLayout(QHBoxLayout())
        wdg.layout().setContentsMargins(5, 0, 5, 0)
        wdg.layout().setSpacing(0)
        return wdg

    def _add_objective(self) -> QToolBar:
        """Create a QToolBar with the `ObjectivesWidget`."""
        obj_toolbar = QToolBar("Objectives", self)
        obj_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.setStyleSheet(GROUPBOX_STYLE)
        # TODO: add this directly to ObjectivesWidget
        self.obj_wdg = ObjectivesWidget()
        self.obj_wdg.setMinimumWidth(0)
        self.obj_wdg._mmc.events.systemConfigurationLoaded.connect(self._resize_obj)
        self.obj_wdg._combo.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        wdg.layout().addWidget(self.obj_wdg)
        obj_toolbar.addWidget(wdg)

        return obj_toolbar

    # TODO: add this directly to ObjectivesWidget
    def _resize_obj(self) -> None:
        self.obj_wdg._combo.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.obj_wdg.setMinimumWidth(0)
        self.obj_wdg._combo.adjustSize()

    def _add_snap_live_toolbar(self) -> QToolBar:
        """Create a QToolBar with the `SnapButton` and `LiveButton`."""
        snap_live_toolbar = QToolBar("Snap Live", self)
        snap_live_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.layout().setSpacing(3)
        wdg.setStyleSheet("border: 0px;")

        snap_btn = SnapButton()
        snap_btn.setText("")
        snap_btn.setToolTip("Snap")
        snap_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        wdg.layout().addWidget(snap_btn)

        live_btn = LiveButton()
        live_btn.setText("")
        live_btn.setToolTip("Live Mode")
        live_btn.button_text_off = ""
        live_btn.button_text_on = ""
        live_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        wdg.layout().addWidget(live_btn)

        snap_live_toolbar.addWidget(wdg)

        return snap_live_toolbar

    def _add_channels(self) -> QToolBar:
        """Create a QToolBar with the `ChannelWidget`."""
        ch_toolbar = QToolBar("Channels", self)
        ch_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.setStyleSheet(GROUPBOX_STYLE)

        ch_lbl = QLabel(text="Channel:")
        wdg.layout().addWidget(ch_lbl)
        wdg.layout().addWidget(ChannelWidget())

        ch_toolbar.addWidget(wdg)

        return ch_toolbar

    def _add_exposure(self) -> QToolBar:
        """Create a QToolBar with the `DefaultCameraExposureWidget`."""
        exp_toolbar = QToolBar("Exposure", self)
        exp_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.setStyleSheet(GROUPBOX_STYLE)

        exposure_wdg = DefaultCameraExposureWidget()
        exp_lbl = QLabel(text="Exposure:")
        exp_layout = cast(QHBoxLayout, exposure_wdg.layout())
        exp_layout.setContentsMargins(0, 0, 0, 0)
        exp_layout.setSpacing(3)
        exp_layout.insertWidget(0, exp_lbl)
        wdg.layout().addWidget(exposure_wdg)

        exp_toolbar.addWidget(wdg)

        return exp_toolbar

    def _add_shutter_toolbar(self) -> QToolBar:
        """Create a QToolBar with the `MMShuttersWidget`."""
        shutters_toolbar = QToolBar("Shutters", self)
        shutters_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.layout().setSpacing(3)
        wdg.setStyleSheet("border: 0px;")

        shutter_wdg = MMShuttersWidget()
        shutter_wdg.setMinimumHeight(TOOL_SIZE)
        wdg.layout().addWidget(shutter_wdg)

        shutters_toolbar.addWidget(wdg)

        return shutters_toolbar

    def _add_tools_toolsbar(self) -> QToolBar:
        """Add a QToolBar containing QPushButtons for pymmcore-widgets.

        e.g. Property Browser, GroupPresetTableWidget, ...

        QPushButtons are connected to the `_show_dock_widget` method.

        The QPushButton.whatsThis() property is used to store the key that
        will be used by the `_show_dock_widget` method.
        """
        tools_toolbar = QToolBar("Tools", self)
        tools_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = self._create_groupbox()
        wdg.layout().setSpacing(3)
        wdg.setStyleSheet("border: 0px;")

        for key in DOCK_WIDGETS:
            btn_icon = DOCK_WIDGETS[key][1]
            if btn_icon is None:
                continue
            btn = self._make_tool_button(key, btn_icon)
            btn.setWhatsThis(key)
            btn.clicked.connect(self._show_dock_widget)
            wdg.layout().addWidget(btn)

        tools_toolbar.addWidget(wdg)

        return tools_toolbar

    def _make_tool_button(self, tooltip: str, btn_icon: str) -> QPushButton:
        """Create the QPushbutton for the tools QToolBar."""
        btn = QPushButton()
        btn.setToolTip(tooltip)
        btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        btn.setIcon(icon(btn_icon, color=(0, 255, 0)))
        btn.setIconSize(QSize(30, 30))
        return btn

    def _add_plugins_toolbar(self) -> QToolBar:
        """Add a QToolBar containing plugins QPushButtons.

        e.g. MDA, Explore, ...

        QPushButtons are connected to the `_show_dock_widget` method.

        The QPushButton.whatsThis() property is used to store the key that
        will be used by the `_show_dock_widget` method.
        """
        plgs_toolbar = QToolBar("Plugins")
        plgs_toolbar.setMinimumHeight(TOOLBAR_SIZE)

        wdg = QGroupBox()
        wdg.setLayout(QHBoxLayout())
        wdg.layout().setContentsMargins(5, 0, 5, 0)
        wdg.layout().setSpacing(3)
        wdg.setStyleSheet("border: 0px;")

        mda = self._make_plugin_button("MDA", "MultiDimensional Acquisition")
        explorer = self._make_plugin_button(
            "Explorer", "MultiDimensional Grid Acquisition"
        )
        wdg.layout().addWidget(mda)
        wdg.layout().addWidget(explorer)

        plgs_toolbar.addWidget(wdg)

        return plgs_toolbar

    def _make_plugin_button(self, btn_text: str, tooltip: str) -> QPushButton:
        """Create the QPushButton for the plugins QToolBar."""
        btn = QPushButton(text=btn_text)
        btn.setToolTip(tooltip)
        btn.setMinimumHeight(TOOL_SIZE)
        btn.setWhatsThis(btn_text)
        btn.clicked.connect(self._show_dock_widget)
        return btn

    def _show_dock_widget(self, key: str = "") -> None:
        """Look up widget class in DOCK_WIDGETS and add/create or show/raise.

        `key` must be a key in the DOCK_WIDGETS dict or a `str` stored in
        the `whatsThis` property of a `sender` `QPushButton`.
        """
        floating = False
        tabify = True
        if not key:
            # using QPushButton.whatsThis() property to get the key.
            btn = cast(QPushButton, self.sender())
            key = btn.whatsThis()

        if key in self._dock_widgets:
            # already exists
            dock_wdg = self._dock_widgets[key]
            dock_wdg.show()
            dock_wdg.raise_()
        else:
            # creating it for the first time
            # sourcery skip: extract-method
            try:
                wdg_cls = DOCK_WIDGETS[key][0]
            except KeyError as e:
                raise KeyError(
                    "Not a recognized dock widget key. "
                    f"Must be one of {list(DOCK_WIDGETS)} "
                    " or the `whatsThis` property of a `sender` `QPushButton`."
                ) from e
            wdg = wdg_cls(parent=self, mmcore=self._mmc)

            if isinstance(wdg, PropertyBrowser):
                wdg.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
                )
                wdg._prop_table.setVerticalScrollBarPolicy(
                    Qt.ScrollBarPolicy.ScrollBarAlwaysOff
                )
                floating = True
                tabify = False

            dock_wdg = self._add_dock_widget(wdg, key, floating=floating, tabify=tabify)
            self._dock_widgets[key] = dock_wdg

    def _add_dock_widget(
        self, widget: QWidget, name: str, floating: bool = False, tabify: bool = False
    ) -> QDockWidget:
        """Add a docked widget using napari's add_dock_widget."""
        dock_wdg = self.viewer.window.add_dock_widget(
            widget,
            name=name,
            area="right",
            tabify=tabify,
        )
        with contextlib.suppress(AttributeError):
            dock_wdg._close_btn = False
        dock_wdg.setFloating(floating)
        return dock_wdg
