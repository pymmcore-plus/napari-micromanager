from micromanager_gui.qmmcore import QMMCore
from useq import MDASequence

mmc = QMMCore()
mmc.loadSystemConfiguration()

mda = MDASequence(
    axis_order="tzpc",
    stage_positions=[(10, 20, 30), (50, 50, 50)],
    channels=[dict(config="Cy5", exposure=50), dict(config="FITC", exposure=100.0)],
    time_plan=dict(interval=3, loops=3),
    z_plan=dict(range=1.0, step=0.5),
)

mmc.run_mda(mda)
