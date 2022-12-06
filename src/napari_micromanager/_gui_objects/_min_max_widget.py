from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from qtpy.QtWidgets import QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QWidget

if TYPE_CHECKING:
    from napari.layers import Image

QCOLORS = set(QColor.colorNames())


class MinMax(QScrollArea):
    """A Widget to display min and max layer grey values."""

    def __init__(self, *, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel()

        lbl = QLabel("(min, max)")
        lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        central = QWidget()
        central.setLayout(QHBoxLayout())
        central.layout().setContentsMargins(0, 0, 0, 0)
        central.layout().addWidget(lbl)
        central.layout().addWidget(self._label)
        self.setWidget(central)

    def update_from_layers(self, layers: Iterable[Image]) -> None:
        """Update the minmax label based on data from layers."""
        min_max_txt = ""
        for layer in layers:
            col = col if (col := layer.colormap.name) in QCOLORS else "gray"
            try:
                minmax = tuple(layer._calc_data_range(mode="slice"))
            except Exception:
                import warnings

                warnings.warn("cannot update minmax. napari api changed?")
                continue
            min_max_txt += f'<font color="{col}">{minmax}</font>'

        self._label.setText(min_max_txt)
