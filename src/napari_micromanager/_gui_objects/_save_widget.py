from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

if TYPE_CHECKING:
    from napari_micromanager._mda_meta import SequenceMeta


class SaveWidget(QGroupBox):
    """A Widget to gather information about MDA file saving."""

    def __init__(
        self, title: str = "Save Acquisition", parent: QWidget | None = None
    ) -> None:
        super().__init__(title, parent)
        self.setCheckable(True)

        # directory
        self._directory = QLineEdit()
        self._browse_save_btn = QPushButton(text="...")
        self._browse_save_btn.clicked.connect(self._request_save_path)
        # filename
        self._fname = QLineEdit("Experiment")
        # checkbox for splitting files by position
        self._split_pos_checkbox = QCheckBox(
            text="Save XY Positions in separate files (ImageJ compatibility)"
        )

        grid = QGridLayout()
        self.setLayout(grid)
        grid.setSpacing(10)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.addWidget(QLabel("Directory:"), 0, 0)
        grid.addWidget(self._directory, 0, 1)
        grid.addWidget(self._browse_save_btn, 0, 2)
        grid.addWidget(QLabel("File Name:"), 1, 0)
        grid.addWidget(self._fname, 1, 1)
        grid.addWidget(self._split_pos_checkbox, 2, 0, 1, 3)

    def _request_save_path(self) -> None:
        save_dir = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if save_dir:
            self._directory.setText(save_dir)

    def get_state(self) -> dict:
        """Return current state of the dialog.

        All keys in this dict must kwargs for `SequenceMeta`.
        """
        return {
            "file_name": self._fname.text(),
            "save_dir": self._directory.text(),
            "save_pos": self._split_pos_checkbox.isChecked(),
            "should_save": self.isChecked(),
        }

    def set_state(self, meta: SequenceMeta) -> None:
        self.setChecked(meta.should_save)
        self._fname.setText(meta.file_name)
        self._directory.setText(meta.save_dir)
        self._split_pos_checkbox.setChecked(meta.save_pos)
