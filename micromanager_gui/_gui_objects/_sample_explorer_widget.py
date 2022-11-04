from pathlib import Path
from typing import Optional, cast

from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import SampleExplorerWidget
from qtpy.QtCore import Signal
from qtpy.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)
from useq import MDASequence

from .._mda_meta import SEQUENCE_META, SequenceMeta


class SampleExplorer(SampleExplorerWidget):
    """napari-micromanager Explorer Widget GUI."""

    metadataInfo = Signal(SequenceMeta, MDASequence)

    def __init__(
        self, parent: Optional[QWidget] = None, *, mmcore: Optional[CMMCorePlus] = None
    ) -> None:
        super().__init__(include_run_button=True, parent=parent, mmcore=mmcore)

        self.save_explorer_groupBox = self._create_save_group()
        v_layout = cast(QVBoxLayout, self.explorer_wdg.layout())
        v_layout.insertWidget(0, self.save_explorer_groupBox)

        self.checkbox = self._create_radiobtn()
        v_layout.insertWidget(4, self.checkbox)

        self.browse_save_explorer_Button.clicked.connect(self._set_explorer_dir)
        self.start_scan_Button.clicked.connect(self._send_meta)

    def _create_save_group(self) -> QGroupBox:

        group = QGroupBox(title="Save Scan")
        group.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed))
        group.setCheckable(True)
        group.setChecked(False)
        group_layout = QVBoxLayout()
        group_layout.setSpacing(10)
        group_layout.setContentsMargins(10, 10, 10, 10)
        group.setLayout(group_layout)

        # directory
        dir_group = QWidget()
        dir_group_layout = QHBoxLayout()
        dir_group_layout.setSpacing(5)
        dir_group_layout.setContentsMargins(0, 10, 0, 5)
        dir_group.setLayout(dir_group_layout)
        lbl_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        min_lbl_size = 80
        btn_sizepolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        dir_lbl = QLabel(text="Directory:")
        dir_lbl.setMinimumWidth(min_lbl_size)
        dir_lbl.setSizePolicy(lbl_sizepolicy)
        self.dir_explorer_lineEdit = QLineEdit()
        self.browse_save_explorer_Button = QPushButton(text="...")
        self.browse_save_explorer_Button.setSizePolicy(btn_sizepolicy)
        dir_group_layout.addWidget(dir_lbl)
        dir_group_layout.addWidget(self.dir_explorer_lineEdit)
        dir_group_layout.addWidget(self.browse_save_explorer_Button)

        # filename
        fname_group = QWidget()
        fname_group_layout = QHBoxLayout()
        fname_group_layout.setSpacing(5)
        fname_group_layout.setContentsMargins(0, 5, 0, 10)
        fname_group.setLayout(fname_group_layout)
        fname_lbl = QLabel(text="File Name:")
        fname_lbl.setMinimumWidth(min_lbl_size)
        fname_lbl.setSizePolicy(lbl_sizepolicy)
        self.fname_explorer_lineEdit = QLineEdit()
        self.fname_explorer_lineEdit.setText("Experiment")
        fname_group_layout.addWidget(fname_lbl)
        fname_group_layout.addWidget(self.fname_explorer_lineEdit)

        group_layout.addWidget(dir_group)
        group_layout.addWidget(fname_group)

        return group

    def _create_radiobtn(self) -> QGroupBox:

        group = QGroupBox(title="Display as:")
        group.setChecked(False)
        group_layout = QHBoxLayout()
        group_layout.setSpacing(7)
        group_layout.setContentsMargins(10, 15, 10, 15)
        group.setLayout(group_layout)

        fixed_policy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.radiobtn = QRadioButton(text=" grid (layers translation)")
        self.radiobtn.setSizePolicy(fixed_policy)
        self.radiobtn.setChecked(True)
        self.multid_stack_checkbox = QRadioButton(text=" multi-dimensional stack")
        self.multid_stack_checkbox.setSizePolicy(fixed_policy)

        group_layout.addWidget(self.radiobtn)

        spacer = QSpacerItem(30, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        group_layout.addItem(spacer)
        group_layout.addWidget(self.multid_stack_checkbox)

        spacer = QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Expanding)
        group_layout.addItem(spacer)

        return group

    def _set_explorer_dir(self) -> None:
        # set the directory
        self.dir = QFileDialog(self)
        self.dir.setFileMode(QFileDialog.DirectoryOnly)
        self.save_dir = QFileDialog.getExistingDirectory(self.dir)
        self.dir_explorer_lineEdit.setText(self.save_dir)
        self.parent_path = Path(self.save_dir)

    def _create_translation_points(self, rows: int, cols: int) -> list:

        cam_size_x = self._mmc.getROI(self._mmc.getCameraDevice())[2]
        cam_size_y = self._mmc.getROI(self._mmc.getCameraDevice())[3]
        move_x = cam_size_x - (self.ovelap_spinBox.value() * cam_size_x) / 100
        move_y = cam_size_y - (self.ovelap_spinBox.value() * cam_size_y) / 100
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

    def _set_translate_point_list(self) -> list:

        t_list = self._create_translation_points(self.scan_size_r, self.scan_size_c)
        if self.stage_tableWidget.rowCount() > 0:
            t_list = t_list * self.stage_tableWidget.rowCount()
        return t_list

    def _send_meta(self) -> None:
        sequence = self.get_state()
        SEQUENCE_META[sequence] = SequenceMeta(
            mode="explorer",
            should_save=self.save_explorer_groupBox.isChecked(),
            file_name=self.fname_explorer_lineEdit.text(),
            save_dir=self.dir_explorer_lineEdit.text()
            or str(Path(__file__).parent.parent.parent),
            translate_explorer=self.radiobtn.isChecked(),
            explorer_translation_points=self._set_translate_point_list(),
        )

        self.metadataInfo.emit(SEQUENCE_META[sequence], self.get_state())
