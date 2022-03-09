from itertools import chain, product, repeat

from fonticon_mdi6 import MDI6
from pymmcore_plus import DeviceType
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGridLayout, QPushButton, QSpinBox, QWidget
from superqt.fonticon import setTextIcon

from .. import _core

PREFIX = MDI6.__name__.lower()
STAGE_DEVICES = {DeviceType.Stage, DeviceType.XYStage, DeviceType.AutoFocus}
STYLE = """
QPushButton {
    border: none;
    background: transparent;
    color: rgb(0, 180, 0);
}
QPushButton:hover:!pressed {
    color: rgb(0, 255, 0);
}
QPushButton:pressed {
    color: rgb(0, 100, 0);
}
QSpinBox {
    min-width: 40px;
    height: 20px;
}
"""


class StageWidget(QWidget):
    # fmt: off
    BTNS = {
        # btn glyph                (r, c, xmag, ymag)
        MDI6.chevron_triple_up:    (0, 3,  0,  3),
        MDI6.chevron_double_up:    (1, 3,  0,  2),
        MDI6.chevron_up:           (2, 3,  0,  1),
        MDI6.chevron_down:         (4, 3,  0, -1),
        MDI6.chevron_double_down:  (5, 3,  0, -2),
        MDI6.chevron_triple_down:  (6, 3,  0, -3),
        MDI6.chevron_triple_left:  (3, 0, -3,  0),
        MDI6.chevron_double_left:  (3, 1, -2,  0),
        MDI6.chevron_left:         (3, 2, -1,  0),
        MDI6.chevron_right:        (3, 4,  1,  0),
        MDI6.chevron_double_right: (3, 5,  2,  0),
        MDI6.chevron_triple_right: (3, 6,  3,  0),
    }
    # fmt: on

    def __init__(self, levels=2, device=None, mmcore=None):
        super().__init__()
        self._mmc = mmcore or _core.get_core_singleton()
        self._device = device or self._mmc.getXYStageDevice()
        self._dtype = self._mmc.getDeviceType(self._device)
        self.setStyleSheet(STYLE)
        assert self._dtype in STAGE_DEVICES, f"{self._dtype} not in {STAGE_DEVICES}"

        self.setLayout(QGridLayout())
        self.layout().setSpacing(0)
        self._snap_on_click = True

        self._step = QSpinBox()
        self._step.setValue(10)
        self._step.setMaximum(9999)
        self._step.valueChanged.connect(self._update_ttips)
        self._step.clearFocus()
        self._step.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self._step.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for glpyh, (row, col, xmag, ymag) in self.BTNS.items():
            btn = QPushButton()
            btn.setFlat(True)
            btn.setFixedSize(33, 33)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            setTextIcon(btn, glpyh)
            btn.clicked.connect(self._on_click)
            self.layout().addWidget(btn, row, col, Qt.AlignmentFlag.AlignCenter)

        # self._step.setStyleSheet("background:transparent; border: 0;")
        self.layout().addWidget(self._step, 3, 3, Qt.AlignmentFlag.AlignCenter)
        self._set_visible_levels(levels)
        self._set_xy_visible()
        self._update_ttips()

    def _update_ttips(self):
        coords = chain(zip(repeat(3), range(7)), zip(range(7), repeat(3)))

        Y = {DeviceType.XYStage: "Y", DeviceType.AutoFocus: "Offset"}.get(
            self._dtype, "Z"
        )

        for r, c in coords:
            if item := self.layout().itemAtPosition(r, c):
                if (r, c) == (3, 3):
                    continue
                if btn := item.widget():
                    xmag, ymag = self.BTNS[f"{PREFIX}.{btn.text()}"][-2:]
                    if xmag:
                        btn.setToolTip(f"move X by {self._scale(xmag)} µm")
                    elif ymag:
                        btn.setToolTip(f"move {Y} by {self._scale(ymag)} µm")

    def _set_xy_visible(self):
        if self._dtype is not DeviceType.XYStage:
            for c in (0, 1, 2, 4, 5, 6):
                if item := self.layout().itemAtPosition(3, c):
                    item.widget().hide()

    def _set_visible_levels(self, levels: int):
        """Hide upper-level stage buttons as desired. Levels must be between 1-3."""
        assert 1 <= levels <= 3, "levels must be between 1-3"
        self._levels = levels
        for btn in self.findChildren(QPushButton):
            btn.show()
        if levels < 3:
            # hide row/col 0, 6
            for r, c in product(range(7), (0, 6)):
                if item := self.layout().itemAtPosition(r, c):
                    item.widget().hide()
                if item := self.layout().itemAtPosition(c, r):
                    item.widget().hide()
        if levels < 2:
            # hide row/col 1, 5
            for r, c in product(range(1, 6), (1, 5)):
                if item := self.layout().itemAtPosition(r, c):
                    item.widget().hide()
                if item := self.layout().itemAtPosition(c, r):
                    item.widget().hide()

    def _on_click(self):
        btn: QPushButton = self.sender()
        xmag, ymag = self.BTNS[f"{PREFIX}.{btn.text()}"][-2:]
        self._move_stage(self._scale(xmag), self._scale(ymag))

    def _move_stage(self, x, y):
        if self._dtype is DeviceType.XYStage:
            self._mmc.setRelativeXYPosition(self._device, x, y)
        elif self._dtype is DeviceType.AutoFocus:
            self._mmc.setAutoFocusOffset(y)
        else:
            self._mmc.setRelativePosition(self._device, y)
        if self._snap_on_click:
            self._mmc.snap()

    def _scale(self, mag: int):
        """Convert step mag of (1, 2, 3) to absolute XY units

        Can be used to step 1x field of view, etc...
        """
        return mag * self._step.value()


if __name__ == "__main__":
    from pymmcore_plus import CMMCorePlus
    from qtpy.QtWidgets import QApplication

    core = CMMCorePlus.instance()
    core.loadSystemConfiguration()

    app = QApplication([])

    wdg = StageWidget()
    wdg.show()

    app.exec_()
