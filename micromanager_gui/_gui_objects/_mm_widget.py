from __future__ import annotations

from pymmcore_widgets import (
    ConfigurationWidget,
    GroupPresetTableWidget,
    ObjectivesWidget,
    SliderDialog,
)
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from superqt import QCollapsible

from ._mda_widget import MultiDWidget
from ._sample_explorer_widget import SampleExplorer
from ._shutters_widget import MMShuttersWidget
from ._tab_widget import MMTabWidget
from ._xyz_stages import MMStagesWidget


class MicroManagerWidget(QWidget):
    """GUI elements for the Main Window."""

    def __init__(self) -> None:
        super().__init__()
        # sub_widgets
        self.cfg_wdg = ConfigurationWidget()
        self.obj_wdg = ObjectivesWidget()
        self.stage_wdg = MMStagesWidget()
        self.illum_btn = QPushButton("Light Sources")
        self.illum_btn.clicked.connect(self._show_illum_dialog)
        self.tab_wdg = MMTabWidget()
        self.shutter_wdg = MMShuttersWidget()
        self.mda = MultiDWidget()
        self.explorer = SampleExplorer()

        self.setLayout(QVBoxLayout())
        self.layout().setSpacing(10)
        self.layout().setContentsMargins(10, 10, 10, 10)

        # general scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wdg = self._create_gui()
        scroll.setWidget(self._wdg)
        self.layout().addWidget(scroll)

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
        # add microscope collapsible
        self.mic_group = QGroupBox()
        self.mic_group_layout = QVBoxLayout()
        self.mic_group_layout.setSpacing(0)
        self.mic_group_layout.setContentsMargins(1, 0, 1, 1)
        coll_sizepolicy = QSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self.mic_coll = QCollapsible(title="Microscope")
        self.mic_coll.layout().setSpacing(0)
        self.mic_coll.layout().setContentsMargins(0, 0, 0, 0)
        self.mic_coll.setSizePolicy(coll_sizepolicy)

        # add objective, property browser, illumination and camera widgets
        obj_prop = self.add_mm_objectives_widget()
        ill_shutter = self.add_shutter_widgets()
        self.mic_coll.addWidget(obj_prop)
        self.mic_coll.addWidget(ill_shutter)
        self.mic_coll.expand(animate=False)
        self.mic_group_layout.addWidget(self.mic_coll)
        self.mic_group.setLayout(self.mic_group_layout)
        main_layout.addWidget(self.mic_group)

        # add stages collapsible
        self.stages_group = QGroupBox()
        self.stages_group_layout = QVBoxLayout()
        self.stages_group_layout.setSpacing(0)
        self.stages_group_layout.setContentsMargins(1, 0, 1, 1)

        self.stages_coll = QCollapsible(title="Stages")
        self.stages_coll.setSizePolicy(coll_sizepolicy)
        self.stages_coll.layout().setSpacing(0)
        self.stages_coll.layout().setContentsMargins(0, 0, 0, 0)
        self.stages_coll.addWidget(self.stage_wdg)
        self.stages_coll.expand(animate=False)

        self.stages_group_layout.addWidget(self.stages_coll)
        self.stages_group.setLayout(self.stages_group_layout)
        main_layout.addWidget(self.stages_group)

        self.group_preset_table_wdg = GroupPresetTableWidget()

        # add tab widget
        main_layout.addWidget(self.tab_wdg)
        self.tab_wdg.tabWidget.addTab(self.mda, "Multi-D Acquisition")
        self.tab_wdg.tabWidget.addTab(self.explorer, "Sample Explorer")
        self.tab_wdg.tabWidget.addTab(self.group_preset_table_wdg, "Groups and Presets")

        return wdg

    def add_mm_objectives_widget(self):
        obj_wdg = QWidget()
        obj_wdg_layout = QHBoxLayout()
        obj_wdg_layout.setContentsMargins(5, 5, 5, 5)
        obj_wdg_layout.setSpacing(7)
        obj_wdg_layout.addWidget(self.obj_wdg)
        obj_wdg.setLayout(obj_wdg_layout)
        return obj_wdg

    def add_shutter_widgets(self):
        shutter_wdg = QWidget()
        shutter_wdg_layout = QHBoxLayout()
        shutter_wdg_layout.setContentsMargins(5, 5, 5, 5)
        shutter_wdg_layout.setSpacing(7)
        shutter_wdg_layout.addWidget(self.shutter_wdg)
        shutter_wdg_layout.addWidget(self.illum_btn)
        shutter_wdg.setLayout(shutter_wdg_layout)
        return shutter_wdg

    def _show_illum_dialog(self):
        if not hasattr(self, "_illumination"):
            self._illumination = SliderDialog("(Intensity|Power|test)s?", parent=self)
        self._illumination.show()
