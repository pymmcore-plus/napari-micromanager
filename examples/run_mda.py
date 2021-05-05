import atexit
import threading

from micromanager_gui._core._client import detatched_mmcore
from micromanager_gui._core.qmmcore import QCoreListener
from Pyro5.api import Daemon
from qtpy.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from useq import MDASequence

mda = MDASequence(
    axis_order="tpcz",
    time_plan=dict(interval=1.3, loops=10),
    stage_positions=[(10, 20, 30)],
    channels=[dict(config="Cy5", exposure=100)],
    z_plan=dict(range=1.0, step=0.5),
)


app = QApplication([])


def new_func(mda):
    daemon = Daemon()
    qlistener = QCoreListener()
    daemon.register(qlistener)
    thread = threading.Thread(target=daemon.requestLoop, daemon=True)
    thread.start()
    proc = detatched_mmcore(config="demo")
    proc.core.connect_callback_handler(qlistener)
    proc.core.loadSystemConfiguration()
    proc.core.run_mda(mda)
    atexit.register(proc.kill)
    return proc.core


core = new_func(mda)

w = QWidget()

btn1 = QPushButton("quit")
btn2 = QPushButton("stop")
btn3 = QPushButton("pause/go")
btn1.clicked.connect(app.quit)
btn2.clicked.connect(lambda x: core.abort())
btn3.clicked.connect(lambda x: core.toggle_pause())

w.setLayout(QVBoxLayout())
w.layout().addWidget(btn1)
w.layout().addWidget(btn2)
w.layout().addWidget(btn3)
w.show()

app.exec_()
