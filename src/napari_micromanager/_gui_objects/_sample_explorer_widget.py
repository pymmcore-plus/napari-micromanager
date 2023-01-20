from __future__ import annotations

from typing import cast

from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import SampleExplorerWidget
from qtpy.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QRadioButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)
from useq import MDASequence

from .._mda_meta import SEQUENCE_META_KEY, SequenceMeta
from ._save_widget import SaveWidget


class SampleExplorer(SampleExplorerWidget):
    """napari-micromanager Explorer Widget GUI."""

    def __init__(
        self, *, parent: QWidget | None = None, mmcore: CMMCorePlus | None = None
    ) -> None:
        super().__init__(include_run_button=True, parent=parent, mmcore=mmcore)

        self.channel_groupbox.setMinimumHeight(175)

        self._save_groupbox = SaveWidget("Save Scan")
        self._save_groupbox._split_pos_checkbox.hide()
        self._save_groupbox.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self._save_groupbox.setChecked(False)

        v_layout = cast(QVBoxLayout, self._central_widget.layout())
        v_layout.insertWidget(0, self._save_groupbox)

        self.checkbox = self._create_radiobtn()
        v_layout.insertWidget(4, self.checkbox)

    def _create_radiobtn(self) -> QGroupBox:

        group = QGroupBox(title="Display as:")
        group.setChecked(False)
        group_layout = QHBoxLayout()
        group_layout.setSpacing(7)
        group_layout.setContentsMargins(10, 15, 10, 15)
        group.setLayout(group_layout)

        fixed_policy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.radiobtn_grid = QRadioButton(text=" grid (layers translation)")
        self.radiobtn_grid.setSizePolicy(fixed_policy)
        self.radiobtn_grid.setChecked(True)
        self.radiobtn_multid_stack = QRadioButton(text=" multi-dimensional stack")
        self.radiobtn_multid_stack.setSizePolicy(fixed_policy)

        group_layout.addWidget(self.radiobtn_grid)

        spacer = QSpacerItem(30, 10, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        group_layout.addItem(spacer)

        group_layout.addWidget(self.radiobtn_multid_stack)

        spacer = QSpacerItem(
            10, 10, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        group_layout.addItem(spacer)

        return group

    def _create_translation_points(
        self, rows: int, cols: int
    ) -> list[tuple[float, float, int, int]]:

        cam_size_x = self._mmc.getROI(self._mmc.getCameraDevice())[2]
        cam_size_y = self._mmc.getROI(self._mmc.getCameraDevice())[3]
        move_x = (
            cam_size_x - (self.grid_params.overlap_spinBox.value() * cam_size_x) / 100
        )
        move_y = (
            cam_size_y - (self.grid_params.overlap_spinBox.value() * cam_size_y) / 100
        )
        x = -((cols - 1) * (cam_size_x / 2))
        y = (rows - 1) * (cam_size_y / 2)

        # for 'snake' acquisition
        points = []
        for r in range(rows):
            if r % 2:  # for odd rows
                col = cols - 1
                for c in range(cols):
                    if c == 0:
                        y -= move_y
                    points.append((x, y, r, c))
                    if col > 0:
                        col -= 1
                        x -= move_x
            else:  # for even rows
                for c in range(cols):
                    if r > 0 and c == 0:
                        y -= move_y
                    points.append((x, y, r, c))
                    if c < cols - 1:
                        x += move_x
        return points

    def _set_translate_point_list(self) -> list[tuple[float, float, int, int]]:

        t_list = self._create_translation_points(
            self.grid_params.scan_size_spinBox_r.value(),
            self.grid_params.scan_size_spinBox_c.value(),
        )
        if self.position_groupbox._table.rowCount() > 0:
            t_list = t_list * self.position_groupbox._table.rowCount()
        return t_list

    def get_state(self) -> MDASequence:
        sequence = cast(MDASequence, super().get_state())
        # override save_pos from SaveWidget
        save_state: dict = {**self._save_groupbox.get_state(), "save_pos": False}
        sequence.metadata[SEQUENCE_META_KEY] = SequenceMeta(
            mode="explorer",
            **save_state,
            translate_explorer=self.radiobtn_grid.isChecked(),
            explorer_translation_points=self._set_translate_point_list(),
            scan_size_c=self.grid_params.scan_size_spinBox_c.value(),
            scan_size_r=self.grid_params.scan_size_spinBox_r.value(),
        )
        return sequence
