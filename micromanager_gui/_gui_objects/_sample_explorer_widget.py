from pathlib import Path
from typing import List, Optional, Tuple, cast

from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import SampleExplorerWidget
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

from .._mda_meta import SEQUENCE_META, SequenceMeta


class SampleExplorer(SampleExplorerWidget):
    """napari-micromanager Explorer Widget GUI."""

    def __init__(
        self, *, parent: Optional[QWidget] = None, mmcore: Optional[CMMCorePlus] = None
    ) -> None:
        super().__init__(include_run_button=True, parent=parent, mmcore=mmcore)

        self.channel_groupbox.setMinimumHeight(175)

        self.save_explorer_groupbox = self._create_save_group()
        v_layout = cast(QVBoxLayout, self.explorer_wdg.layout())
        v_layout.insertWidget(0, self.save_explorer_groupbox)

        self.checkbox = self._create_radiobtn()
        v_layout.insertWidget(4, self.checkbox)

        self.browse_save_explorer_Button.clicked.connect(self._set_explorer_dir)

    def _create_save_group(self) -> QGroupBox:

        group = QGroupBox(title="Save Scan")
        group.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
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
        lbl_sizepolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        min_lbl_size = 80
        btn_sizepolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
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

    def _set_explorer_dir(self) -> None:
        # set the directory
        self.dir = QFileDialog(self)
        self.dir.setFileMode(QFileDialog.FileMode.DirectoryOnly)
        self.save_dir = QFileDialog.getExistingDirectory(self.dir)
        self.dir_explorer_lineEdit.setText(self.save_dir)
        self.parent_path = Path(self.save_dir)

    def _create_translation_points(
        self, rows: int, cols: int
    ) -> List[Tuple[float, float, int, int]]:

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

    def _set_translate_point_list(self) -> List[Tuple[float, float, int, int]]:

        t_list = self._create_translation_points(self.scan_size_r, self.scan_size_c)
        if self.stage_pos_groupbox.stage_tableWidget.rowCount() > 0:
            t_list = t_list * self.stage_pos_groupbox.stage_tableWidget.rowCount()
        return t_list

    def _start_scan(self) -> None:
        """Run the MDA sequence experiment."""

        # construct a `useq.MDASequence` object from the values inserted in the widget
        experiment = self.get_state()

        SEQUENCE_META[experiment] = SequenceMeta(
            mode="explorer",
            should_save=self.save_explorer_groupbox.isChecked(),
            file_name=self.fname_explorer_lineEdit.text(),
            save_dir=self.dir_explorer_lineEdit.text()
            or str(Path(__file__).parent.parent.parent),
            translate_explorer=self.radiobtn_grid.isChecked(),
            explorer_translation_points=self._set_translate_point_list(),
            scan_size_c=self.scan_size_c,
            scan_size_r=self.scan_size_r,
        )

        # run the MDA experiment asynchronously
        self._mmc.run_mda(experiment)  # run the MDA experiment asynchronously
        return
