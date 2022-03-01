from typing import Optional

from qtpy import QtWidgets as QtW


class MMConfigurationWidget(QtW.QGroupBox):
    """Widget to select and load MM configuration."""

    def __init__(self, parent: Optional[QtW.QWidget] = None) -> None:
        super().__init__(parent)

        self.setTitle("Micro-Manager Configuration")

        self.cfg_LineEdit = QtW.QLineEdit()
        self.cfg_LineEdit.setPlaceholderText("MMConfig_demo.cfg")

        self.browse_cfg_Button = QtW.QPushButton("...")
        self.browse_cfg_Button.clicked.connect(self._browse_cfg)

        self.load_cfg_Button = QtW.QPushButton("Load")
        self.load_cfg_Button.clicked.connect(self.load_cfg)

        self.setLayout(QtW.QHBoxLayout())
        self.layout().addWidget(self.cfg_LineEdit)
        self.layout().addWidget(self.browse_cfg_Button)
        self.layout().addWidget(self.load_cfg_Button)

    def _browse_cfg(self) -> None:
        """Open file dialog to select a config file."""
        (filename, _) = QtW.QFileDialog.getOpenFileName(
            self, "Select a Micro-Manager configuration file", "", "cfg(*.cfg)"
        )
        if filename:
            self.cfg_LineEdit.setText(filename)

    def load_cfg(self) -> None:
        """Load the config path currently in the line_edit."""
        from .. import _core

        _core.load_system_config(self.cfg_LineEdit.text())
