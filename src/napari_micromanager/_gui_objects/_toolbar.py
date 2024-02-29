from __future__ import annotations

import base64
import contextlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Tuple, cast

from fonticon_mdi6 import MDI6
from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import (
    CameraRoiWidget,
    ChannelGroupWidget,
    ChannelWidget,
    ConfigurationWidget,
    DefaultCameraExposureWidget,
    GroupPresetTableWidget,
    LiveButton,
    ObjectivesWidget,
    PropertyBrowser,
    SnapButton,
)

try:
    # this was renamed
    from pymmcore_widgets import ObjectivesPixelConfigurationWidget
except ImportError:
    from pymmcore_widgets import PixelSizeWidget as ObjectivesPixelConfigurationWidget

import appdirs
from qtpy.QtCore import QByteArray, QEvent, QObject, QSize, Qt
from qtpy.QtWidgets import (
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
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

TOOL_SIZE = 35

# Path to the user data directory to store the layout
USER_DATA_DIR = Path(appdirs.user_data_dir(appname="napari_micromanager"))
USER_LAYOUT_PATH = USER_DATA_DIR / "napari_micromanager_layout.json"


# Dict for QObject and its QPushButton icon
DOCK_WIDGETS: Dict[str, Tuple[type[QWidget], str | None]] = {  # noqa: U006
    "Device Property Browser": (PropertyBrowser, MDI6.table_large),
    "Groups and Presets Table": (GroupPresetTableWidget, MDI6.table_large_plus),
    "Illumination Control": (IlluminationWidget, MDI6.lightbulb_on),
    "Stages Control": (MMStagesWidget, MDI6.arrow_all),
    "Camera ROI": (CameraRoiWidget, MDI6.crop),
    "Pixel Size Table": (ObjectivesPixelConfigurationWidget, MDI6.ruler),
    "MDA": (MultiDWidget, None),
}


class MicroManagerToolbar(QMainWindow):
    """Create a QToolBar for the Main Window."""

    def __init__(self, viewer: napari.viewer.Viewer) -> None:
        super().__init__()

        self._mmc = CMMCorePlus.instance()
        self.viewer: napari.viewer.Viewer = getattr(viewer, "__wrapped__", viewer)

        # add variables to the napari console
        if console := getattr(self.viewer.window._qt_viewer, "console", None):
            from useq import MDAEvent, MDASequence

            console.push(
                {
                    "MDAEvent": MDAEvent,
                    "MDASequence": MDASequence,
                    "mmcore": self._mmc,
                }
            )

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
            ConfigToolBar(self),
            ChannelsToolBar(self),
            ObjectivesToolBar(self),
            None,
            ShuttersToolBar(self),
            SnapLiveToolBar(self),
            ExposureToolBar(self),
            ToolsToolBar(self),
        ]
        for item in toolbar_items:
            if item:
                self.addToolBar(Qt.ToolBarArea.TopToolBarArea, item)
            else:
                self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)

        self._is_initialized = False
        self.installEventFilter(self)

    def _initialize(self) -> None:
        if self._is_initialized or not (
            win := getattr(self.viewer.window, "_qt_window", None)
        ):
            return
        win = cast(QMainWindow, win)
        if (
            isinstance(dw := self.parent(), QDockWidget)
            and win.dockWidgetArea(dw) is not Qt.DockWidgetArea.TopDockWidgetArea
        ):
            self._is_initialized = True
            was_visible = dw.isVisible()
            win.removeDockWidget(dw)
            dw.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea)
            win.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, dw)
            dw.setVisible(was_visible)  # necessary after using removeDockWidget
            self.removeEventFilter(self)

    def eventFilter(self, obj: QObject | None, event: QEvent | None) -> bool:
        """Event filter that ensures that this widget is shown at the top.

        npe2 plugins don't have a way to specify where they should be added, so this
        event filter listens for the event when this widget is docked in the main
        window, then redocks it at the top and assigns allowed areas.
        """
        # the move event is one of the first events that is fired when the widget is
        # docked, so we use it to re-dock this widget at the top
        if (
            event
            and event.type() == QEvent.Type.Move
            and obj is self
            and not self._is_initialized
        ):
            self._initialize()

        return False

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

            wdg = ScrollableWidget(self, title=key, widget=wdg)
            dock_wdg = self._add_dock_widget(wdg, key, floating=floating, tabify=tabify)
            self._connect_dock_widget(dock_wdg)
            dock_wdg.destroyed.connect(self._disconnect_dock_widget)
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
        # fix napari bug that makes dock widgets too large
        with contextlib.suppress(AttributeError):
            self.viewer.window._qt_window.resizeDocks(
                [dock_wdg], [widget.sizeHint().width() + 20], Qt.Orientation.Horizontal
            )
        with contextlib.suppress(AttributeError):
            dock_wdg._close_btn = False
        dock_wdg.setFloating(floating)
        return dock_wdg

    def _connect_dock_widget(self, dock_wdg: QDockWidget) -> None:
        """Connect the dock widget to the main window."""
        dock_wdg.visibilityChanged.connect(self._save_layout)
        dock_wdg.topLevelChanged.connect(self._save_layout)
        dock_wdg.dockLocationChanged.connect(self._save_layout)

    def _disconnect_dock_widget(self) -> None:
        """Disconnect the dock widget from the main window."""
        dock_wdg = cast(QDockWidget, self.sender())
        dock_wdg.visibilityChanged.disconnect(self._save_layout)
        dock_wdg.topLevelChanged.disconnect(self._save_layout)
        dock_wdg.dockLocationChanged.disconnect(self._save_layout)

    def _on_dock_widget_changed(self) -> None:
        """Start a saving threrad to save the layout if the thread is not running."""

    def _save_layout(self) -> None:
        """Save the napa-micromanager layout to a json file.

        The json file has two keys:
        - "layout_state" where the state of napari main window is stored using the
          saveState() method. The state is base64 encoded to be able to save it to the
          json file.
        - "pymmcore_widgets" where the names of the docked pymmcore_widgets are stored.

        IMPORTANT: The "pymmcore_widgets" key is crucial in our layout saving process.
        It stores the names of all active pymmcore_widgets at the time of saving. Before
        restoring the layout, we must recreate these widgets. If not, they won't be
        included in the restored layout.
        """
        if getattr(self.viewer.window, "_qt_window", None) is None:
            return
        # get the names of the pymmcore_widgets that are part of the layout
        pymmcore_wdgs: list[str] = []
        main_win = self.viewer.window._qt_window
        for dock_wdg in main_win.findChildren(QDockWidget):
            wdg_name = dock_wdg.objectName()
            if wdg_name in DOCK_WIDGETS:
                pymmcore_wdgs.append(wdg_name)

        # get the state of the napari main window as bytes
        state_bytes = main_win.saveState().data()

        # Create dictionary with widget names and layout state. The layout state is
        # base64 encoded to be able to save it to a json file.
        data = {
            "pymmcore_widgets": pymmcore_wdgs,
            "layout_state": base64.b64encode(state_bytes).decode(),
        }

        # if the user layout path does not exist, create it
        if not USER_LAYOUT_PATH.exists():
            USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

        try:
            with open(USER_LAYOUT_PATH, "w") as json_file:
                json.dump(data, json_file)
        except Exception as e:
            print(f"Was not able to save layout to file. Error: {e}")

    def _load_layout(self) -> None:
        """Load the napari-micromanager layout from a json file."""
        if not USER_LAYOUT_PATH.exists():
            return

        try:
            with open(USER_LAYOUT_PATH) as f:
                data = json.load(f)

                # get the layout state bytes
                state_bytes = data.get("layout_state")

                if state_bytes is None:
                    return

                # add pymmcore_widgets to the main window
                pymmcore_wdgs = data.get("pymmcore_widgets", [])
                for wdg_name in pymmcore_wdgs:
                    if wdg_name in DOCK_WIDGETS:
                        self._show_dock_widget(wdg_name)

                # Convert base64 encoded string back to bytes
                state_bytes = base64.b64decode(state_bytes)

                # restore the layout state
                self.viewer.window._qt_window.restoreState(QByteArray(state_bytes))

        except Exception as e:
            print(f"Was not able to load layout from file. Error: {e}")


class ScrollableWidget(QWidget):
    """A QWidget with a QScrollArea.

    We use it to add a croll alre to the pymmcore_widgets.
    """

    def __init__(self, parent: QWidget | None = None, *, title: str, widget: QWidget):
        super().__init__(parent)
        self.setWindowTitle(title)
        # create the scroll area and add the widget to it
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        layout = QHBoxLayout(self)
        layout.addWidget(self.scroll_area)
        # set the widget to the scroll area
        self.scroll_area.setWidget(widget)
        # resize the dock widget to the size hint of the widget
        self.resize(widget.minimumSizeHint())


# -------------- Toolbars --------------------


class MMToolBar(QToolBar):
    def __init__(self, title: str, parent: QWidget = None) -> None:
        super().__init__(title, parent)
        self.setMinimumHeight(48)
        self.setObjectName(f"MM-{title}")

        self.frame = QFrame()
        gb_layout = QHBoxLayout(self.frame)
        gb_layout.setContentsMargins(0, 0, 0, 0)
        gb_layout.setSpacing(2)
        self.addWidget(self.frame)

    def addSubWidget(self, wdg: QWidget) -> None:
        cast("QHBoxLayout", self.frame.layout()).addWidget(wdg)


class ConfigToolBar(MMToolBar):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Configuration", parent)
        self.addSubWidget(ConfigurationWidget())
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class ObjectivesToolBar(MMToolBar):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Objectives", parent=parent)
        self._wdg = ObjectivesWidget()
        self.addSubWidget(self._wdg)


class ChannelsToolBar(MMToolBar):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Channels", parent)
        self.addSubWidget(QLabel(text="Channel:"))
        self.addSubWidget(ChannelGroupWidget())
        self.addSubWidget(ChannelWidget())


class ExposureToolBar(MMToolBar):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Exposure", parent)
        self.addSubWidget(QLabel(text="Exposure:"))
        self.addSubWidget(DefaultCameraExposureWidget())


class SnapLiveToolBar(MMToolBar):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Snap Live", parent)
        snap_btn = SnapButton()
        snap_btn.setText("")
        snap_btn.setToolTip("Snap")
        snap_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.addSubWidget(snap_btn)

        live_btn = LiveButton()
        live_btn.setText("")
        live_btn.setToolTip("Live Mode")
        live_btn.button_text_off = ""
        live_btn.button_text_on = ""
        live_btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        self.addSubWidget(live_btn)


class ToolsToolBar(MMToolBar):
    """A QToolBar containing QPushButtons for pymmcore-widgets.

    e.g. Property Browser, GroupPresetTableWidget, ...

    QPushButtons are connected to the `_show_dock_widget` method.

    The QPushButton.whatsThis() property is used to store the key that
    will be used by the `_show_dock_widget` method.
    """

    def __init__(self, parent: MicroManagerToolbar) -> None:
        super().__init__("Tools", parent)

        if not isinstance(parent, MicroManagerToolbar):
            raise TypeError("parent must be a MicroManagerToolbar instance.")

        for key in DOCK_WIDGETS:
            btn_icon = DOCK_WIDGETS[key][1]
            if btn_icon is None:
                continue

            btn = QPushButton()
            btn.setToolTip(key)
            btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
            btn.setIcon(icon(btn_icon, color=(0, 255, 0)))
            btn.setIconSize(QSize(30, 30))
            btn.setWhatsThis(key)
            btn.clicked.connect(parent._show_dock_widget)
            self.addSubWidget(btn)

        btn = QPushButton("MDA")
        btn.setToolTip("MultiDimensional Acquisition")
        btn.setFixedSize(TOOL_SIZE, TOOL_SIZE)
        btn.setWhatsThis("MDA")
        btn.clicked.connect(parent._show_dock_widget)
        self.addSubWidget(btn)


class ShuttersToolBar(MMToolBar):
    def __init__(self, parent: QWidget) -> None:
        super().__init__("Shutters", parent)
        self.addSubWidget(MMShuttersWidget())
