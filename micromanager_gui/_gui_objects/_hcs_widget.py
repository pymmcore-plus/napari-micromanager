from pathlib import Path
from typing import Optional

from pymmcore_plus import CMMCorePlus
from pymmcore_widgets import HCSWidget
from qtpy.QtCore import Signal
from qtpy.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)
from useq import MDASequence

from .._mda_meta import SEQUENCE_META, SequenceMeta


class HCSWidgetMain(HCSWidget):
    """napari-micromanager HCS Widget GUI."""

    metadataInfo = Signal(SequenceMeta, MDASequence)

    def __init__(
        self, parent: Optional[QWidget] = None, *, mmcore: Optional[CMMCorePlus] = None
    ) -> None:
        super().__init__(include_run_button=True, parent=parent, mmcore=mmcore)

        self.saving_tab = self._create_save_wdg()
        self.tabwidget.addTab(self.saving_tab, "  Saving  ")

        self.browse_save_Button.clicked.connect(self._set_hcs_dir)
        self.run_Button.clicked.connect(self._send_meta)

    def _create_save_wdg(self) -> QWidget:

        wdg = QWidget()
        wdg_layout = QVBoxLayout()
        wdg_layout.setSpacing(0)
        wdg_layout.setContentsMargins(10, 10, 10, 10)
        wdg.setLayout(wdg_layout)
        save_group = self._create_save_group()
        wdg_layout.addWidget(save_group)

        verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        wdg_layout.addItem(verticalSpacer)

        return wdg

    def _create_save_group(self) -> QGroupBox:

        self.save_hcs_groupBox = QGroupBox(title="Save HCS Acquisition")
        self.save_hcs_groupBox.setSizePolicy(
            QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        )
        self.save_hcs_groupBox.setCheckable(True)
        self.save_hcs_groupBox.setChecked(False)
        group_layout = QVBoxLayout()
        group_layout.setSpacing(10)
        group_layout.setContentsMargins(10, 10, 10, 10)
        self.save_hcs_groupBox.setLayout(group_layout)

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
        self.dir_lineEdit = QLineEdit()
        self.browse_save_Button = QPushButton(text="...")
        self.browse_save_Button.setSizePolicy(btn_sizepolicy)
        self.browse_save_Button.clicked.connect(self._set_hcs_dir)
        dir_group_layout.addWidget(dir_lbl)
        dir_group_layout.addWidget(self.dir_lineEdit)
        dir_group_layout.addWidget(self.browse_save_Button)

        # filename
        fname_group = QWidget()
        fname_group_layout = QHBoxLayout()
        fname_group_layout.setSpacing(5)
        fname_group_layout.setContentsMargins(0, 5, 0, 10)
        fname_group.setLayout(fname_group_layout)
        fname_lbl = QLabel(text="File Name: ")
        fname_lbl.setMinimumWidth(min_lbl_size)
        fname_lbl.setSizePolicy(lbl_sizepolicy)
        self.fname_lineEdit = QLineEdit()
        self.fname_lineEdit.setText("HCS")
        fname_group_layout.addWidget(fname_lbl)
        fname_group_layout.addWidget(self.fname_lineEdit)

        group_layout.addWidget(dir_group)
        group_layout.addWidget(fname_group)

        return self.save_hcs_groupBox

    def _set_hcs_dir(self) -> None:

        # set the directory
        self.dir = QFileDialog(self)
        self.dir.setFileMode(QFileDialog.DirectoryOnly)
        self.save_dir = QFileDialog.getExistingDirectory(self.dir)
        self.dir_lineEdit.setText(self.save_dir)
        self.parent_path = Path(self.save_dir)

    def _send_meta(self) -> None:
        sequence = self.get_state()
        SEQUENCE_META[sequence] = SequenceMeta(
            mode="hcs",
            should_save=self.save_hcs_groupBox.isChecked(),
            file_name=self.fname_lineEdit.text(),
            save_dir=self.dir_lineEdit.text()
            or str(Path(__file__).parent.parent.parent),
        )

        self.metadataInfo.emit(SEQUENCE_META[sequence], self.get_state())
