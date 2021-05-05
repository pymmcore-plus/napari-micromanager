from micromanager_gui._core._client import detatched_mmcore
from useq import MDASequence

mda = MDASequence(
    axis_order="tpcz",
    time_plan=dict(interval=5, loops=3),
    stage_positions=[(10, 20, 30), (0, 0, 0)],
    channels=[dict(config="Cy5", exposure=100)],
    z_plan=dict(range=1.0, step=0.25),
)


with detatched_mmcore(config="demo") as proc:
    proc.core.run_mda(mda)
