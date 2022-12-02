from __future__ import annotations

from pymmcore_widgets import (
    CameraRoiWidget,
    ConfigurationWidget,
    GroupPresetTableWidget,
    ObjectivesWidget,
    PixelSizeWidget,
    PropertyBrowser,
)
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from ._illumination_widget import IlluminationWidget
from ._mda_widget import MultiDWidget
from ._min_max_widget import MinMax
from ._sample_explorer_widget import SampleExplorer
from ._snap_live_widget import SnapLiveWidget
from ._stages_widget import MMStagesWidget


class MicroManagerWidget(QWidget):
    """GUI elements for the Main Window."""

    def __init__(self) -> None:
        super().__init__()

        # widgets
        self.illumination = IlluminationWidget(parent=self)
        self.stages = MMStagesWidget(parent=self)
        self.cam_roi = CameraRoiWidget()
        self.prop_browser = PropertyBrowser(parent=self)
        self.prop_browser.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.prop_browser._prop_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.px_size_table = PixelSizeWidget(parent=self)
        self.group_preset_wdg = GroupPresetTableWidget()
        self.mda = MultiDWidget(parent=self)
        self.explorer = SampleExplorer(parent=self)
        self.minmax = MinMax(parent=self)

        self.cfg_wdg = ConfigurationWidget()
        self.obj_wdg = ObjectivesWidget()
        self.snap_live = SnapLiveWidget()

        self.setLayout(QVBoxLayout())
        self.layout().setSpacing(10)
        self.layout().setContentsMargins(10, 10, 10, 10)

        main_wdg = self._create_gui()
        self.layout().addWidget(main_wdg)

    def _create_gui(self) -> QWidget:

        # main widget
        wdg = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 0, 10, 0)
        main_layout.setSpacing(3)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wdg.setLayout(main_layout)
        # add cfg_wdg
        main_layout.addWidget(self.cfg_wdg)
        # add objective
        obj = self.add_mm_objectives_widget()
        main_layout.addWidget(obj)
        # add snap_live
        main_layout.addWidget(self.snap_live)

        # spacer
        spacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        main_layout.addItem(spacer)

        return wdg

    def add_mm_objectives_widget(self):
        obj_wdg = QGroupBox()
        obj_wdg_layout = QHBoxLayout()
        obj_wdg_layout.setContentsMargins(5, 5, 5, 5)
        obj_wdg_layout.setSpacing(7)
        obj_wdg_layout.addWidget(self.obj_wdg)
        obj_wdg.setLayout(obj_wdg_layout)
        return obj_wdg
