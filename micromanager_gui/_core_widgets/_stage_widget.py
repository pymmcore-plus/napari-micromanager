from fonticon_mdi6 import MDI6
from qtpy.QtWidgets import QGridLayout, QPushButton, QWidget
from superqt.fonticon import icon

BTNS = [
    (MDI6.chevron_triple_up, 0, 3),
    (MDI6.chevron_double_up, 1, 3),
    (MDI6.chevron_up, 2, 3),
    (MDI6.chevron_down, 4, 3),
    (MDI6.chevron_double_down, 5, 3),
    (MDI6.chevron_triple_down, 6, 3),
    (MDI6.chevron_triple_left, 3, 0),
    (MDI6.chevron_double_left, 3, 1),
    (MDI6.chevron_left, 3, 2),
    (MDI6.chevron_right, 3, 4),
    (MDI6.chevron_double_right, 3, 5),
    (MDI6.chevron_triple_right, 3, 6),
]


class StageWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QGridLayout())
        self.layout().setSpacing(0)

        for glpyh, row, col in BTNS:
            btn = QPushButton()
            btn.setFixedSize(40, 40)
            btn.setFocusPolicy()
            btn.setIcon(icon(glpyh))
            self.layout().addWidget(btn, row, col)


if __name__ == "__main__":
    from qtpy.QtWidgets import QApplication

    app = QApplication([])

    wdg = StageWidget()
    wdg.show()

    app.exec_()
