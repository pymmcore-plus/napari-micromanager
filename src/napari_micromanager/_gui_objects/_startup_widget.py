from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import cast

from platformdirs import user_config_dir
from pymmcore_plus import find_micromanager
from qtpy.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

USER_DIR = Path(user_config_dir("napari_micromanager"))
USER_CONFIGS_PATHS = USER_DIR / "system_configurations.json"
FIXED = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
NEW = "New Configuration"


class StartupDialog(QDialog):
    """A dialog to select the MicroManager configuration files."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("System Configurations")

        # label
        cfg_lbl = QLabel("Configuration file:")
        cfg_lbl.setSizePolicy(FIXED)

        # combo box
        self.cfg_combo = QComboBox()
        # `AdjustToMinimumContents` is not available in all qtpy backends so using
        # `AdjustToMinimumContentsLengthWithIcon` instead
        self.cfg_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )

        # browse button
        self.browse_btn = QPushButton("...")
        self.browse_btn.setSizePolicy(FIXED)
        self.browse_btn.clicked.connect(self._on_browse_clicked)

        # Create OK and Cancel buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # add widgets to layout
        wdg_layout = QGridLayout(self)
        wdg_layout.addWidget(cfg_lbl, 0, 0)
        wdg_layout.addWidget(self.cfg_combo, 0, 1)
        wdg_layout.addWidget(self.browse_btn, 0, 2)
        wdg_layout.addWidget(button_box, 2, 0, 1, 3)

        self._initialize()

    def value(self) -> str:
        """Return the selected value."""
        return str(self.cfg_combo.currentText())

    def add_path_to_json(self, path: Path | str) -> None:
        """Uopdate the json file with the new path."""
        if isinstance(path, Path):
            path = str(path)

        # Read the existing data
        try:
            with open(USER_CONFIGS_PATHS) as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {"paths": []}

        # Append the new path. using insert so we leave the empty string at the end
        paths = cast(list, data.get("paths", []))
        if path not in paths:
            paths.insert(0, path)

        # Write the data back to the file
        with open(USER_CONFIGS_PATHS, "w") as f:
            json.dump({"paths": paths}, f)

    def _initialize(self) -> None:
        """Initialize the dialog with the configuration files."""
        # create USER_CONFIGS_PATHS if it doesn't exist
        if not USER_CONFIGS_PATHS.exists():
            USER_DIR.mkdir(parents=True, exist_ok=True)
            with open(USER_CONFIGS_PATHS, "w") as f:
                json.dump({"paths": []}, f)

        # get the paths from the json file
        configs_paths = self._get_config_paths()

        # add the paths to the combo box
        self.cfg_combo.addItems([*configs_paths, NEW])

        # write the data back to the file
        with open(USER_CONFIGS_PATHS, "w") as f:
            json.dump({"paths": configs_paths}, f)

    def _get_config_paths(self) -> list[str]:
        """Return the paths from the json file.

        If a file stored in the json file doesn't exist, it is removed from the list.

        The method also adds all the .cfg files in the MicroManager folder to the list
        if they are not already there.
        """
        try:
            with open(USER_CONFIGS_PATHS) as f:
                data = json.load(f)

            # get path list from json file
            paths = cast(list, data.get("paths", []))

            # remove any path that doesn't exist
            for path in paths:
                if not Path(path).exists():
                    paths.remove(path)

            # get all the .cfg files in the MicroManager folder
            cfg_files = self._get_micromanager_cfg_files()

            # add all the .cfg files to the list if they are not already there
            for cfg in reversed(cfg_files):
                if str(cfg) not in paths:
                    # using insert so we leave the empty string at the end
                    paths.insert(0, str(cfg))

        except json.JSONDecodeError:
            paths = []
            warnings.warn("Error reading the json file.", stacklevel=2)

        return paths

    def _get_micromanager_cfg_files(self) -> list[Path]:
        """Return all the .cfg files in the MicroManager folders."""
        mm_dir = find_micromanager()

        if mm_dir is None:
            return []

        cfg_files: list[Path] = []
        cfg_files.extend(Path(mm_dir).glob("*.cfg"))

        return cfg_files

    def _on_browse_clicked(self) -> None:
        """Open a file dialog to select a file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open file", "", "MicroManager files (*.cfg)"
        )
        if path:
            # using insert so we leave the empty string at the end
            self.cfg_combo.insertItem(0, path)
            self.cfg_combo.setCurrentText(path)
            self.add_path_to_json(path)
