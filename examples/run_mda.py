import sys

import Pyro5
from micromanager_gui._core._client import detatched_mmcore
from qtpy.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from useq import MDASequence

sys.excepthook = Pyro5.errors.excepthook

mda = MDASequence(
    axis_order="tpzc",
    time_plan=dict(interval=1.3, loops=10),
    stage_positions=[(10, 20, 30)],
    channels=[dict(config="Cy5", exposure=100)],
    z_plan=dict(range=1.0, step=0.5),
)


app = QApplication([])

proc = detatched_mmcore(config="demo")

w = QWidget()

btn1 = QPushButton("quit")
btn2 = QPushButton("stop")
btn3 = QPushButton("pause/go")
btn1.clicked.connect(app.quit)
btn2.clicked.connect(lambda x: proc.core.abort())
btn3.clicked.connect(lambda x: proc.core.toggle_pause())

w.setLayout(QVBoxLayout())
w.layout().addWidget(btn1)
w.layout().addWidget(btn2)
w.layout().addWidget(btn3)
w.show()

proc.core.run_mda(mda)
app.exec_()
