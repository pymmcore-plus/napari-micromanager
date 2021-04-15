from qtpy.QtCore import QCoreApplication

app = QCoreApplication([])
from micromanager_gui.qmmcore import QMMCore
from micromanager_gui._controller import Controller

# from pycromanager import Acquisition
from useq import MDASequence

c = Controller(QMMCore)

def _on_mda_frame(self, img, event):
    print("RECVEIVE FRAME", event)


c.worker.mda_frame_ready.connect(print)
c.loadSystemConfiguration()

mda = MDASequence(
    axis_order="tzpc",
    stage_positions=[(10, 20, 30)],
    channels=[dict(config="Cy5", exposure=100)],
    time_plan=dict(interval=3, loops=4),
    z_plan=dict(range=1.0, step=0.5),
)

c.run_mda(mda)

# with Acquisition('/Users/talley/Desktop/out/', name='hi') as ac:
#     ac.acquire(mda.to_pycromanager())

print("hi")
# app.exec_()