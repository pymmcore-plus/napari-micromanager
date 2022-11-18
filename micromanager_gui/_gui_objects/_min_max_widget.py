from typing import Optional

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QHBoxLayout, QLabel, QScrollArea, QWidget


class MinMax(QWidget):
    """A Widget to display min and max layer grey values."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        max_min_wdg = QWidget()
        max_min_wdg_layout = QHBoxLayout()
        max_min_wdg_layout.setContentsMargins(0, 0, 0, 0)
        max_min_wdg.setLayout(max_min_wdg_layout)

        self.max_min_val_label_name = QLabel()
        self.max_min_val_label_name.setText("(min, max)")
        self.max_min_val_label_name.setMaximumWidth(70)
        max_min_wdg_layout.addWidget(self.max_min_val_label_name)

        self.max_min_val_label = QLabel()
        max_min_wdg_layout.addWidget(self.max_min_val_label)

        scroll.setWidget(max_min_wdg)
        self.layout().addWidget(scroll)
